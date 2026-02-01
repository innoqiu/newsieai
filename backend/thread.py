from typing import Dict, Any
from datetime import datetime, timedelta
import pytz # Timezone handling
from scheduler_config import scheduler
from task import execute_periodic_scan
from engine.x_from_topic import search_x_topic
def _clear_previous_jobs(thread_id: str):
    """
    Remove all existing jobs for this thread_id to avoid duplicates
    when user updates their schedule.
    
    Handles both interval jobs (id = thread_id) and daily jobs (id = thread_id_HHMM).
    
    Args:
        thread_id: The thread identifier to clear jobs for
    """
    if not thread_id:
        return
    
    cleared_count = 0
    jobs_to_remove = []
    
    # Collect all jobs that match this thread_id
    for job in scheduler.get_jobs():
        job_id = job.id
        
        # Match exact thread_id (for interval jobs) or thread_id_* pattern (for daily jobs)
        if job_id == thread_id or job_id.startswith(f"{thread_id}_"):
            jobs_to_remove.append(job)
    
    # Remove collected jobs
    for job in jobs_to_remove:
        try:
            job.remove()
            cleared_count += 1
            print(f"[System] Cleared old job: {job.id}")
        except Exception as e:
            print(f"[Warning] Failed to remove job {job.id}: {e}")
    
    if cleared_count > 0:
        print(f"[System] Cleared {cleared_count} job(s) for thread_id: {thread_id}")

def _get_timezone(tz_str: str):
    """Safe timezone retrieval with fallback to UTC"""
    try:
        if not tz_str:
            return pytz.timezone('Asia/Shanghai') # Default fallback
        return pytz.timezone(tz_str)
    except pytz.UnknownTimeZoneError:
        print(f"[Warning] Unknown timezone '{tz_str}', defaulting to UTC")
        return pytz.utc

def handle_request(thread_structure: Dict[str, Any]) -> None:
    """
    Main entry point for processing the frontend request.
    """
    thread_id = thread_structure.get('thread_id')
    user_name = thread_structure.get('name', 'User')
    schedule_info = thread_structure.get('notification_schedule')
    blocks = thread_structure.get('blocks', [])
    results = []
    for block in blocks:
        block_type = block.get('type', '').lower()
        mode = block.get('ai', 'selective')  # Default mode if not specified
        
        # Handle tags (new format) or body (legacy format)
        tags = block.get('tags', [])
        body = block.get('body', '')
        
        # Convert tags list to body string for engine functions
        # If tags exist, use them; otherwise fall back to body
        if tags and isinstance(tags, list) and len(tags) > 0:
            # Convert tags list to comma-separated string
            if block_type == 'x-from-user':
                # For x-from-user, ensure @ prefix and join
                body = ', '.join([tag if tag.startswith('@') else f'@{tag}' for tag in tags])
            else:
                # For other types, just join with comma
                body = ', '.join(tags)
        elif not body:
            # No tags and no body, skip this block
            print(f"[Worker] Warning: Block {block_type} has no tags or body, skipping")
            continue
        
        print(f"[Worker] Processing block: type={block_type}, tags={tags}, body={body}, mode={mode}")
            
    print(f"\n[API] Processing request for: {thread_id}")

    # 1. Clear old jobs first to avoid duplicates when updating
    _clear_previous_jobs(thread_id)
    
    if not schedule_info:
        print("[API] No schedule found. Running once immediately.")
        execute_periodic_scan(thread_id, 'manual_run', thread_structure, user_name)
        return

    sch_type = schedule_info.get('type')
    
    # 2. Handle Timezone
    # Look for 'timezone' in JSON, default to Shanghai if missing
    user_tz_str = schedule_info.get('timezone', 'Asia/Shanghai')
    user_tz = _get_timezone(user_tz_str)
    print(user_tz)

    # === TYPE A: INTERVAL (e.g., Every 5 hours) ===
    if sch_type == 'interval':
        unit = schedule_info.get('unit', 'minutes')
        interval = int(schedule_info.get('interval', 60))
        
        # Calculate Start Time logic
        start_str = schedule_info.get('startTime', '00:00')
        t_hour, t_min = map(int, start_str.split(':'))
        
        # Get current time in USER'S timezone
        now_in_tz = datetime.now(user_tz)
        start_date = now_in_tz.replace(hour=t_hour, minute=t_min, second=0, microsecond=0)
        
        # If start time passed today, move to tomorrow
        if start_date <= now_in_tz:
            start_date += timedelta(days=1)
            
        scheduler.add_job(
            execute_periodic_scan,
            'interval',
            id=thread_id, # Simple ID for interval
            replace_existing=True, # Safety: replace if somehow still exists
            start_date=start_date,
            timezone=user_tz, # IMPORTANT
            args=[thread_id, 'interval_mode', thread_structure, user_name],
            **{unit: interval}
        )
        print(f"[API] Interval Job added. First run: {start_date} ({user_tz})")
        current_jobs = get_scheduler_status()
        print(current_jobs)

    # === TYPE B: DAILY (e.g., At 17:33 and 05:33) ===
    elif sch_type == 'daily':
        times = schedule_info.get('times', [])
        
        for time_str in times:
            try:
                h_str, m_str = time_str.split(':')
                hour = int(h_str)
                minute = int(m_str)
                print(hour, minute)
                
                # Create unique sub-ID: threadID_HHMM
                job_id = f"{thread_id}_{h_str}{m_str}"
                
                scheduler.add_job(
                    execute_periodic_scan,
                    'cron', # Cron trigger for specific times
                    id=job_id,
                    replace_existing=True, # Safety: replace if somehow still exists
                    hour=hour,
                    minute=minute,
                    second=0,
                    timezone=user_tz, # <--- The Magic: Handles UTC conversion automatically
                    args=[thread_id, 'daily_mode', thread_structure, user_name]
                )
                print(f"[API] Daily Job added for {time_str} ({user_tz}) | JobID: {job_id}")
                current_jobs = get_scheduler_status()
                print(current_jobs)
                
            except ValueError as e:
                print(f"[Error] Failed to add job for {time_str}. Reason: {e}")
                print(f"DEBUG: user_tz type: {type(user_tz)}, value: {user_tz}")

    else:
        print(f"[API] Unknown schedule type: {sch_type}")

def get_scheduler_status():
    """
    获取当前所有等待运行的定时任务
    """
    jobs_data = []
    
    # 1. 直接问调度器要任务列表，而不是去查 SQL
    jobs = scheduler.get_jobs()
    
    for job in jobs:
        try:
            # Extract arguments safely
            args = job.args if hasattr(job, 'args') else []
            
            # Get function name safely
            func_name = str(job.func) if hasattr(job, 'func') else 'unknown'
            
            # Handle next_run_time (can be None)
            next_run = str(job.next_run_time) if job.next_run_time else None
            
            # Extract details based on actual argument structure
            # args = [thread_id, task_type, thread_structure, user_name]
            details = {
                "thread_id": args[0] if len(args) > 0 else None,
                "type": args[1] if len(args) > 1 else None,
                "thread_structure": args[2] if len(args) > 2 else None,  # This is the dict
                "user": args[3] if len(args) > 3 else None,  # This is user_name
            }
            
            jobs_data.append({
                "job_id": job.id,
                "next_run_time": next_run,
                "func_name": func_name,
                "details": details
            })
        except Exception as e:
            # Handle any errors gracefully
            print(f"[Warning] Error processing job {job.id}: {e}")
            jobs_data.append({
                "job_id": job.id,
                "next_run_time": None,
                "func_name": "error",
                "details": {"error": str(e)}
            })
        
    return {
        "total_jobs": len(jobs),
        "jobs": jobs_data
    }