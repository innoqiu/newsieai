import { useState, useEffect, useRef } from 'react'
import './App.css'
import WorkflowStudio from './WorkflowStudio'
import DatabaseOps from './DatabaseOps'
import { auth } from './auth'

const API_BASE_URL = 'http://localhost:8008'

// --- OKX Style SVG Icons ---
const Icons = {
  Logo: () => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" width="24" height="24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><path d="M9 3v18"></path><path d="M15 9h-6"></path><path d="M9 15h6"></path></svg>
  ),
  Database: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>,
  Dashboard: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>,
  Inbox: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9H9l-3-9H2"></path><path d="M7 12V2a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v10"></path></svg>,
  Workflow: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M2 12h20"></path><path d="M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-6"></path><path d="M9 4v16"></path><path d="M15 4v16"></path></svg>,
  User: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>,
  Check: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="20 6 9 17 4 12"></polyline></svg>,
  Alert: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>,
  Close: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>,
  Plus: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>,
  Logout: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>,
  Refresh: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>,
  Trash: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
}

function App() {
  // --- EXISTING STATE (Backend Compatibility Preserved) ---
  const [formData, setFormData] = useState({ name: '', email: '', password: '' })
  const [makeThreadData, setMakeThreadData] = useState({
    notification_schedule: { type: 'daily', times: [''] },
    interests: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
  })
  const [threadBlocks, setThreadBlocks] = useState([]) // Array of block objects
  const [showBlockTypeMenu, setShowBlockTypeMenu] = useState(false)
  const [showProfileOverlay, setShowProfileOverlay] = useState(false)
  const [profileOverlayData, setProfileOverlayData] = useState(null)
  const [profileOverlayLoading, setProfileOverlayLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [result, setResult] = useState(null)

  // --- Thread STATE ---
  const [threads, setThreads] = useState([]) // List of threads
  const [selectedThread, setSelectedThread] = useState(null) // Currently selected thread
  const [threadLoading, setThreadLoading] = useState(false)
  const [threadName, setThreadName] = useState('') // Name for new/updated thread
  const [deleteConfirmThread, setDeleteConfirmThread] = useState(null) // Thread to be deleted

  // --- UI STATE (Web Layout) ---
  const [activePage, setActivePage] = useState('inbox') // 'inbox', 'dashboard', 'account', 'dbopdb'
  const [uiMode, setUiMode] = useState('web') // 'web' or 'workflow'
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [currentUser, setCurrentUser] = useState(null)
  const [authTabMode, setAuthTabMode] = useState('login') // 'login' or 'register'
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [registerName, setRegisterName] = useState('')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [redeemCode, setRedeemCode] = useState('')
  const [topupLoading, setTopupLoading] = useState(false)
  const [topupMessage, setTopupMessage] = useState('')
  const [userProfile, setUserProfile] = useState(null)
  const [profileLoading, setProfileLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState([]) // Chat history for profile section
  const [chatInput, setChatInput] = useState('') // Current chat input
  const chatEndRef = useRef(null) // Ref for auto-scrolling to bottom

  // --- LOGIC HANDLERS (UNTOUCHED) ---
  const handleSubmit = async (e) => {
    e.preventDefault(); if (!formData.password) { setMessage('Password is required'); return; }
    setLoading(true); setMessage(''); setResult(null);
    try {
      const registerResponse = await fetch(`${API_BASE_URL}/api/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: formData.email, password: formData.password, name: formData.name }) });
      const registerData = await registerResponse.json();
      if (registerResponse.ok && registerData.access_token) {
        auth.setToken(registerData.access_token, registerData.user); setIsAuthenticated(true); setCurrentUser(registerData.user); setMessage('Account created!');
        const response = await fetch(`${API_BASE_URL}/api/profile`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: formData.name, email: formData.email, notification_time: '', interests: '', x_usernames: '' }) });
        const data = await response.json(); if (response.ok) { setResult(data); setFormData({ name: '', email: '', password: '' }); }
      } else { setMessage(`Error: ${registerData.detail || 'Failed'}`); }
    } catch (error) { setMessage(`Error: ${error.message}`); } finally { setLoading(false); }
  }

  const handleLoadAndRun = async () => {
    if (!selectedThread && !threadName) { setMessage('Please select or create a thread first'); return; }
    if (!currentUser) { setMessage('Please login first'); return; }
    if (!threadName.trim()) { setMessage('Thread name is required'); return; }
    
    setThreadLoading(true); setMessage('');
    try {
      // Step 1: Save thread to database (integrated save functionality)
      // Clean blocks: remove _inputValue and ensure tags are arrays
      const cleanedBlocks = threadBlocks.map(block => {
        const cleaned = { ...block };
        // Remove internal _inputValue field
        delete cleaned._inputValue;
        // Ensure tags is an array
        if (!cleaned.tags) {
          cleaned.tags = [];
        }
        // Keep body for backward compatibility if tags exist
        if (cleaned.tags && cleaned.tags.length > 0 && !cleaned.body) {
          // Generate body from tags for backward compatibility
          if (block.type === 'x-from-user') {
            cleaned.body = cleaned.tags.map(t => t.startsWith('@') ? t : `@${t}`).join(', ');
          } else {
            cleaned.body = cleaned.tags.join(', ');
          }
        }
        return cleaned;
      });
      
      const threadData = {
        notification_schedule: makeThreadData.notification_schedule,
        interests: makeThreadData.interests,
        blocks: cleanedBlocks,
        timezone: makeThreadData.timezone || 'UTC'
      };

      const saveResponse = await fetch(`${API_BASE_URL}/api/thread/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        },
        body: JSON.stringify({
          thread_id: selectedThread?.thread_id || null,
          name: threadName,
          thread_data: threadData,
          running: false // Will be set to true by start endpoint
        })
      });
      
      const saveData = await saveResponse.json();
      if (!saveResponse.ok) {
        setMessage(saveData.message || 'Failed to save thread');
        return;
      }

      // Step 2: Start the thread (sets running=true and loads into scheduler)
      const threadIdToStart = saveData.thread?.thread_id || selectedThread?.thread_id;
      if (!threadIdToStart) {
        setMessage('Failed to get thread ID');
        return;
      }

      const startResponse = await fetch(`${API_BASE_URL}/api/thread/${threadIdToStart}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        }
      });

      const startData = await startResponse.json();
      if (startResponse.ok) {
        setMessage(`Thread "${threadName}" started successfully`);
        // Reload threads to get updated running status
        await handleLoadThreads();
        // Reload the current thread
        if (threadIdToStart) {
          await handleLoadThread(threadIdToStart);
        }
      } else {
        setMessage(startData.detail || 'Failed to start thread');
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setThreadLoading(false);
    }
  }

  const handleStopRunning = async () => {
    if (!selectedThread) { setMessage('Please select a thread first'); return; }
    if (!currentUser) { setMessage('Please login first'); return; }
    
    setThreadLoading(true); setMessage('');
    try {
      const stopResponse = await fetch(`${API_BASE_URL}/api/thread/${selectedThread.thread_id}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        }
      });

      const stopData = await stopResponse.json();
      if (stopResponse.ok) {
        setMessage(`Thread "${selectedThread.name}" stopped successfully`);
        // Reload threads to get updated running status
        await handleLoadThreads();
        // Reload the current thread
        await handleLoadThread(selectedThread.thread_id);
      } else {
        setMessage(stopData.detail || 'Failed to stop thread');
      }
    } catch (error) {
      setMessage(`Error: ${error.message}`);
    } finally {
      setThreadLoading(false);
    }
  }

  const handleRunPersonalAssistant = async () => {
    if (!selectedThread && !threadName) { setMessage('Please select or create a thread first'); return; }
    if (!currentUser) { setMessage('Please login first'); return; }
    setThreadLoading(true); setMessage('');
    try {
      // Convert notification schedule to legacy format for personal assistant
      let notificationTimes = [];
      if (makeThreadData.notification_schedule?.type === 'daily') {
        notificationTimes = makeThreadData.notification_schedule.times.filter(t => t);
      } else if (makeThreadData.notification_schedule?.type === 'interval') {
        // For interval type, use startTime as the initial time
        if (makeThreadData.notification_schedule.startTime) {
          notificationTimes = [makeThreadData.notification_schedule.startTime];
        }
      }

      // Clean blocks before building thread structure
      const cleanedBlocksForStructure = (threadBlocks || []).map(block => {
        const cleaned = { ...block };
        delete cleaned._inputValue;
        if (!cleaned.tags) cleaned.tags = [];
        return cleaned;
      });
      
      // Build complete thread structure
      const threadStructure = {
        thread_id: selectedThread?.thread_id || null,
        name: threadName || selectedThread?.name || 'Unnamed Thread',
        notification_schedule: makeThreadData.notification_schedule || { type: 'daily', times: [''] },
        interests: makeThreadData.interests || '',
        blocks: cleanedBlocksForStructure,
        timezone: makeThreadData.timezone || 'UTC',
        user_id: currentUser.user_id || currentUser.email.split('@')[0],
        email: currentUser.email,
        profile_data: {
          name: currentUser.name || currentUser.email.split('@')[0],
          email: currentUser.email,
          preferred_notification_times: notificationTimes,
          content_preferences: makeThreadData.interests ? makeThreadData.interests.split(',').map(i => i.trim()).filter(i => i) : [],
          x_usernames: [], // X usernames are now in blocks
          timezone: makeThreadData.timezone || 'UTC'
        }
      };

      const requestData = {
        name: currentUser.name || currentUser.email.split('@')[0],
        email: currentUser.email,
        notification_time: notificationTimes.join(', '),
        interests: makeThreadData.interests || '',
        x_usernames: '',
        thread_structure: threadStructure
      };
      const response = await fetch(`${API_BASE_URL}/api/personal-assistant/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestData) });
      const data = await response.json(); if (response.ok) { setResult(data); setMessage('Assistant completed!'); } else { setMessage(`Error: ${data.detail}`); }
    } catch (error) { setMessage(`Error: ${error.message}`); } finally { setThreadLoading(false); }
  }

  const handleLoadThreads = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    if (!isAuthenticated || !currentUser) { setMessage('Please login first'); return; }
    setThreadLoading(true); setMessage('');
    try {
      const token = auth.getToken();
      const response = await fetch(`${API_BASE_URL}/api/thread/list`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        }
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        setThreads(data.threads || []);
        setMessage(`Loaded ${data.count || 0} thread(s)`);
      } else { setMessage(data.message || 'Failed to load threads'); }
    } catch (error) { setMessage(`Error: ${error.message}`); } finally { setThreadLoading(false); }
  }

  const handleCreateNewThread = async () => {
    if (!isAuthenticated || !currentUser) { setMessage('Please login first'); return; }
    setThreadLoading(true); setMessage('');
    try {
      // Generate default thread name
      const defaultName = `New Thread ${new Date().toLocaleString()}`;

      // Build default thread data structure
      const threadData = {
        notification_schedule: { type: 'daily', times: [''] },
        interests: '',
        blocks: [],
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
      };

      // Initialize form state with timezone
      setMakeThreadData({
        notification_schedule: { type: 'daily', times: [''] },
        interests: '',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
      });

      // Save new thread to backend
      const token = auth.getToken();
      const response = await fetch(`${API_BASE_URL}/api/thread/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        },
        body: JSON.stringify({
          thread_id: null, // Let backend generate new ID
          name: defaultName,
          thread_data: threadData,
          running: false
        })
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        setMessage(`Thread "${defaultName}" created successfully`);
        // Refresh thread list
        await handleLoadThreads();
        // Load the newly created thread
        if (data.thread_id) {
          await handleLoadThread(data.thread_id);
        }
      } else { setMessage(data.message || 'Failed to create thread'); }
    } catch (error) { setMessage(`Error: ${error.message}`); } finally { setThreadLoading(false); }
  }

  const handleLoadThread = async (threadId) => {
    if (!isAuthenticated || !currentUser) { setMessage('Please login first'); return; }
    setThreadLoading(true); setMessage('');
    try {
      const token = auth.getToken();
      const response = await fetch(`${API_BASE_URL}/api/thread/${threadId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        }
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        const thread = data.thread;
        setSelectedThread(thread);
        setThreadName(thread.name);

        // Load thread data into form
        const threadData = thread.thread_data || {};
        // Handle legacy format or new format
        let notificationSchedule = threadData.notification_schedule;
        if (!notificationSchedule && threadData.notification_time) {
          // Convert legacy format to new format
          const times = threadData.notification_time.split(',').map(t => t.trim()).filter(t => t);
          notificationSchedule = { type: 'daily', times: times.length > 0 ? times : [''] };
        } else if (!notificationSchedule) {
          notificationSchedule = { type: 'daily', times: [''] };
        }
        setMakeThreadData({
          notification_schedule: notificationSchedule,
          interests: threadData.interests || '',
          timezone: threadData.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
        });
        // Migrate old blocks to new format
        const migratedBlocks = (threadData.blocks || []).map(block => {
          const migrated = { ...block };
          
          // Migrate old AI values to new method values
          if (block.ai === 'gpt-4o' || block.ai === 'gemini-pro') {
            migrated.ai = block.type === 'x-from-user' ? 'newest' : 'selective';
          }
          
          // Migrate body to tags format
          if (block.body && !block.tags) {
            // Convert body string to tags array
            if (block.type === 'x-from-user') {
              // For x-from-user, split by comma and ensure @ prefix
              const bodyParts = block.body.split(',').map(s => s.trim()).filter(s => s);
              migrated.tags = bodyParts.map(part => {
                const cleaned = part.startsWith('@') ? part : `@${part}`;
                return cleaned;
              });
            } else {
              // For other types, split by comma
              migrated.tags = block.body.split(',').map(s => s.trim()).filter(s => s);
            }
            // Keep body for backward compatibility but prefer tags
            migrated._inputValue = '';
          } else if (!block.tags) {
            // Initialize empty tags if neither body nor tags exist
            migrated.tags = [];
            migrated._inputValue = '';
          } else {
            // Already has tags, just ensure _inputValue exists
            migrated._inputValue = migrated._inputValue || '';
          }
          
          return migrated;
        });
        setThreadBlocks(migratedBlocks);
        setMessage(`Thread "${thread.name}" loaded`);
      } else { setMessage(data.message || 'Failed to load thread'); }
    } catch (error) { setMessage(`Error: ${error.message}`); } finally { setThreadLoading(false); }
  }

  const handleDeleteThread = async (threadId, threadName) => {
    if (!isAuthenticated || !currentUser) { setMessage('Please login first'); return; }
    setThreadLoading(true); setMessage('');
    try {
      const token = auth.getToken();
      const response = await fetch(`${API_BASE_URL}/api/thread/${threadId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        }
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        setMessage(`Thread "${threadName}" deleted successfully`);
        // Clear selection if deleted thread was selected
        if (selectedThread?.thread_id === threadId) {
          setSelectedThread(null);
          setThreadName('');
          setMakeThreadData({
            notification_schedule: { type: 'daily', times: [''] },
            interests: '',
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
          });
          setThreadBlocks([]);
        }
        // Reload threads list
        handleLoadThreads();
      } else { setMessage(data.message || 'Failed to delete thread'); }
    } catch (error) { setMessage(`Error: ${error.message}`); } finally { setThreadLoading(false); setDeleteConfirmThread(null); }
  }

  const handleLogin = async (e) => {
    e.preventDefault(); if (!loginEmail || !loginPassword) { setAuthError('Enter credentials'); return; }
    setAuthLoading(true); setAuthError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: loginEmail, password: loginPassword }) });
      const data = await response.json();
      if (response.ok && data.access_token) { auth.setToken(data.access_token, data.user); setCurrentUser(data.user); setLoginEmail(''); setLoginPassword(''); setIsAuthenticated(true); setActivePage('dashboard'); } else { setAuthError(data.detail || 'Invalid credentials'); }
    } catch (error) { setAuthError(`Error: ${error.message}`); } finally { setAuthLoading(false); }
  }

  const handleRegister = async (e) => {
    e.preventDefault(); if (!registerEmail || !registerPassword) { setAuthError('Enter details'); return; }
    setAuthLoading(true); setAuthError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: registerEmail, password: registerPassword, name: registerName || registerEmail.split('@')[0] }) });
      const data = await response.json();
      if (response.ok && data.access_token) { auth.setToken(data.access_token, data.user); setCurrentUser(data.user); setRegisterEmail(''); setRegisterPassword(''); setIsAuthenticated(true); setActivePage('dashboard'); } else { setAuthError(data.detail || 'Failed'); }
    } catch (error) { setAuthError(`Error: ${error.message}`); } finally { setAuthLoading(false); }
  }

  const handleLogout = () => { auth.clearAuth(); setIsAuthenticated(false); setCurrentUser(null); setUiMode('web'); setActivePage('dashboard'); setUserProfile(null); }

  const handleLoadProfile = async () => {
    if (!isAuthenticated || !currentUser) return;
    setProfileLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/profile/check`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        },
        body: JSON.stringify({ email: currentUser.email })
      });
      const data = await response.json();
      if (response.ok && data.status === 'found') {
        setUserProfile(data.profile);
      } else {
        setUserProfile(null);
      }
    } catch (error) {
      console.error('Error loading profile:', error);
      setUserProfile(null);
    } finally {
      setProfileLoading(false);
    }
  }

  const handleTopup = async (e) => {
    e.preventDefault(); if (!redeemCode) return;
    setTopupLoading(true); setTopupMessage('');
    try {
      if (redeemCode.toLowerCase() === 'friendtoinno') {
        const token = auth.getToken(); if (!token) return;
        const response = await fetch(`${API_BASE_URL}/api/user/add-credits`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...auth.getAuthHeader() }, body: JSON.stringify({ amount: 100 }) });
        const data = await response.json();
        if (response.ok && data.success) { setTopupMessage('Success: +100 Credits'); setCurrentUser(prev => ({ ...prev, credits: (prev?.credits || 0) + 100 })); setRedeemCode(''); } else { setTopupMessage('Failed'); }
      } else { setTopupMessage('Invalid Code'); }
    } catch (error) { setTopupMessage('Error'); } finally { setTopupLoading(false); }
  }

  const handleSendChatMessage = async (messageText) => {
    if (!messageText.trim()) return;
    if (!isAuthenticated || !currentUser) {
      setMessage('Please login first');
      return;
    }
    
    // Add user message to chat history
    const userMessage = {
      sender: 'user',
      text: messageText,
      timestamp: new Date()
    };
    
    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    
    // Show loading indicator
    const loadingMessage = {
      sender: 'bot',
      text: '...',
      timestamp: new Date(),
      isLoading: true
    };
    setChatMessages(prev => [...prev, loadingMessage]);
    
    try {
      // Call the profile manager API endpoint
      const response = await fetch(`${API_BASE_URL}/api/profile/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...auth.getAuthHeader()
        },
        body: JSON.stringify({
          message: messageText,
          user_id: currentUser.user_id || currentUser.email?.split('@')[0],
          email: currentUser.email
        })
      });
      
      const data = await response.json();
      
      // Remove loading message
      setChatMessages(prev => prev.filter(msg => !msg.isLoading));
      
      if (response.ok && data.status === 'success') {
        // Add bot response to chat history
        const botMessage = {
          sender: 'bot',
          text: data.response || 'Profile updated successfully.',
          timestamp: new Date()
        };
        setChatMessages(prev => [...prev, botMessage]);
        
        // Show notification based on tool called
        if (data.notification_type) {
          setTimeout(() => {
            let notificationText = '';
            if (data.notification_type === 'preference_saved') {
              notificationText = 'New Preference Saved';
            } else if (data.notification_type === 'preference_deleted') {
              notificationText = 'Preference Deleted';
            } else if (data.notification_type === 'profile_viewed') {
              notificationText = 'Profile Retrieved';
            }
            
            if (notificationText) {
              const notification = {
                sender: 'system',
                text: notificationText,
                timestamp: new Date(),
                isNotification: true
              };
              setChatMessages(prev => [...prev, notification]);
              
              // Auto-remove notification after 5 seconds
              setTimeout(() => {
                setChatMessages(prev => prev.filter(msg => !msg.isNotification || msg.timestamp !== notification.timestamp));
              }, 5000);
            }
          }, 300);
        }
      } else {
        // Add error message
        const errorMessage = {
          sender: 'bot',
          text: `Error: ${data.detail || data.message || 'Failed to get response'}`,
          timestamp: new Date()
        };
        setChatMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      // Remove loading message
      setChatMessages(prev => prev.filter(msg => !msg.isLoading));
      
      // Add error message
      const errorMessage = {
        sender: 'bot',
        text: `Error: ${error.message || 'Failed to connect to server'}`,
        timestamp: new Date()
      };
      setChatMessages(prev => [...prev, errorMessage]);
    }
  }

  // --- Effects ---
  useEffect(() => {
    const token = auth.getToken(); const user = auth.getUser();
    if (token && user) { setIsAuthenticated(true); setCurrentUser(user); }

    // Handle URL routing for /dbopdb
    const path = window.location.pathname;
    if (path === '/dbopdb' || path === '/dbopdb/') {
      setActivePage('dbopdb');
    }
  }, []);

  // Update URL when page changes
  useEffect(() => {
    if (activePage === 'dbopdb') {
      window.history.pushState({}, '', '/dbopdb');
    } else if (window.location.pathname === '/dbopdb') {
      window.history.pushState({}, '', '/');
    }
  }, [activePage]);

  useEffect(() => {
    if (isAuthenticated && currentUser && activePage === 'account') {
      handleLoadProfile();
    }
  }, [isAuthenticated, currentUser, activePage]);

  // Auto-scroll disabled - page stays in place when messages are sent
  // useEffect(() => {
  //   if (chatEndRef.current) {
  //     chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
  //   }
  // }, [chatMessages]);

  const workflowLoginTriggered = useRef(false);
  useEffect(() => {
    if (uiMode === 'workflow' && !isAuthenticated && !workflowLoginTriggered.current) {
      setUiMode('web'); setActivePage('account'); workflowLoginTriggered.current = true;
    }
  }, [uiMode, isAuthenticated]);

  // --- RENDERING ---

  // 1. Workflow Studio View (Fullscreen overlay)
  if (uiMode === 'workflow') {
    return (
      <div className="app-container-workflow">
        <div style={{ height: '50px', borderBottom: '1px solid #333', display: 'flex', alignItems: 'center', padding: '0 20px', background: '#121214', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'white', fontWeight: '600' }}>
            <Icons.Logo /> <span>Threadful - Beta</span>
          </div>
          <button onClick={() => setUiMode('web')} className="secondary-btn" style={{ padding: '6px 12px', fontSize: '12px' }}>
            Exit to Dashboard
          </button>
        </div>
        <div style={{ height: 'calc(100vh - 50px)' }}>
          <WorkflowStudio />
        </div>
      </div>
    );
  }

  // 2. Main Web Layout
  return (
    <div className="web-layout">
      {/* SIDEBAR */}
      <aside className="web-sidebar">
        <div className="sidebar-header">
          <div className="logo-icon"><Icons.Logo /></div>
          <h1 style={{ fontSize: '1.1rem', fontWeight: '700', letterSpacing: '-0.03em' }}>NewsieAI</h1>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activePage === 'inbox' ? 'active' : ''}`}
            onClick={() => setActivePage('inbox')}
          >
            <Icons.Inbox /> Inbox
          </button>

          <button
            className={`nav-item ${activePage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActivePage('dashboard')}
          >
            <Icons.Dashboard /> My Threads
          </button>

          <button
            className={`nav-item ${uiMode === 'workflow' ? 'active' : ''}`}
            onClick={() => isAuthenticated ? setUiMode('workflow') : setActivePage('account')}
          >
            <Icons.Workflow /> Threadful - Beta
          </button>

          <button
            className={`nav-item ${activePage === 'account' ? 'active' : ''}`}
            onClick={() => setActivePage('account')}
          >
            <Icons.User /> {isAuthenticated ? 'My Account' : 'Login / Register'}
          </button>

          <button
            className={`nav-item ${activePage === 'dbopdb' ? 'active' : ''}`}
            onClick={() => setActivePage('dbopdb')}
          >
            <Icons.Database /> Database Ops
          </button>
        </nav>

        {isAuthenticated && currentUser && (
          <div className="sidebar-footer">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', fontWeight: 'bold' }}>
                {currentUser.name ? currentUser.name[0] : 'U'}
              </div>
              <div style={{ overflow: 'hidden' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: '600', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {currentUser.name || 'User'}
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {currentUser.credits || 0} credits
                </div>
              </div>
            </div>
            <button onClick={handleLogout} className="nav-item" style={{ color: 'var(--accent-red)', paddingLeft: 0 }}>
              <Icons.Logout /> Logout
            </button>
          </div>
        )}
      </aside>

      {/* MAIN CONTENT */}
      <main className="web-main">
        {/* Top Header */}
        <header className="web-header">
          <div className="user-status">
            {isAuthenticated ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent-green)' }}></span>
                Online
              </span>
            ) : (
              <span>Guest Mode</span>
            )}
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="web-content-scroll">

          {/* --- VIEW: INBOX --- */}
          {activePage === 'inbox' && (
            <div className="fade-in">
              {!isAuthenticated ? (
                <div style={{ textAlign: 'center', marginTop: '10vh' }}>
                  <h2>Welcome to NewsieAI</h2>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '10px auto 30px' }}>
                    Your personal AI news assistant. Aggregate, filter, and summarize intelligence from the web and social media.
                  </p>
                  <button onClick={() => setActivePage('account')} className="primary-btn">Get Started</button>
                </div>
              ) : (
                <div className="section-header">
                  <h2>Inbox</h2>
                  <p>Your news feed and notifications will appear here.</p>
                </div>
              )}
            </div>
          )}

          {/* --- VIEW: ACCOUNT / LOGIN --- */}
          {activePage === 'account' && (
            <div className="fade-in" style={{ maxWidth: '800px', margin: '0 auto', width: '100%', padding: '0 1rem' }}>
              <div className="section-header" style={{ textAlign: 'center' }}>
                <h2>{isAuthenticated ? 'Account Settings' : authTabMode === 'login' ? 'Welcome Back' : 'Create Account'}</h2>
                <p>{isAuthenticated ? 'Manage your profile and credits' : 'Access your personal news agent'}</p>
              </div>

              {!isAuthenticated ? (
                <div className="web-card">
                  {authTabMode === 'login' ? (
                    <form onSubmit={handleLogin} className="modern-form">
                      <div className="input-group">
                        <label>Email</label>
                        <input type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} required />
                      </div>
                      <div className="input-group">
                        <label>Password</label>
                        <input type="password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} required />
                      </div>
                      {authError && <div className="status-pill error">{authError}</div>}
                      <button type="submit" disabled={authLoading} className="primary-btn">Log In</button>
                      <div style={{ textAlign: 'center', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>No account? </span>
                        <button type="button" onClick={() => setAuthTabMode('register')} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', textDecoration: 'underline', cursor: 'pointer' }}>Register</button>
                      </div>
                    </form>
                  ) : (
                    <form onSubmit={handleRegister} className="modern-form">
                      <div className="input-group">
                        <label>Name</label>
                        <input type="text" value={registerName} onChange={e => setRegisterName(e.target.value)} />
                      </div>
                      <div className="input-group">
                        <label>Email</label>
                        <input type="email" value={registerEmail} onChange={e => setRegisterEmail(e.target.value)} required />
                      </div>
                      <div className="input-group">
                        <label>Password</label>
                        <input type="password" value={registerPassword} onChange={e => setRegisterPassword(e.target.value)} required />
                      </div>
                      {authError && <div className="status-pill error">{authError}</div>}
                      <button type="submit" disabled={authLoading} className="primary-btn">Create Account</button>
                      <div style={{ textAlign: 'center', fontSize: '0.85rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Have account? </span>
                        <button type="button" onClick={() => setAuthTabMode('login')} style={{ background: 'none', border: 'none', color: 'var(--text-primary)', textDecoration: 'underline', cursor: 'pointer' }}>Log In</button>
                      </div>
                    </form>
                  )}
                </div>
              ) : (
                <>
                  {/* My Profile Section - Chat Interface */}
                  <div className="web-card" style={{ marginBottom: '1.5rem' }}>
                    <div className="section-header" style={{ marginBottom: '1rem' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.5rem' }}>My Profile</h3>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                        Tell NEWSIE about your preferences and interests. Chat to help it understand you better.
                      </p>
                    </div>

                    {/* Chat Container */}
                    <div style={{
                      background: 'var(--bg-input)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      flexDirection: 'column',
                      height: '600px',
                      overflow: 'hidden'
                    }}>
                      {/* Chat Messages Area */}
                      <div className="chat-messages-container" style={{
                        flex: 1,
                        overflowY: 'auto',
                        padding: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '1rem'
                      }}>
                        {chatMessages.length === 0 ? (
                          <div style={{
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            height: '100%',
                            color: 'var(--text-secondary)',
                            textAlign: 'center',
                            gap: '0.5rem'
                          }}>
                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💬</div>
                            <div style={{ fontSize: '0.9rem', fontWeight: '500' }}>Start a conversation</div>
                            <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                              Share your interests, preferences, or ask questions about your profile
                            </div>
                          </div>
                        ) : (
                          chatMessages.map((msg, idx) => {
                            // Handle system notifications
                            if (msg.isNotification) {
                              return (
                                <div
                                  key={idx}
                                  style={{
                                    display: 'flex',
                                    justifyContent: 'center',
                                    margin: '0.5rem 0',
                                    animation: 'fadeIn 0.3s ease-out'
                                  }}
                                >
                                  <div style={{
                                    padding: '0.5rem 1rem',
                                    borderRadius: 'var(--radius-md)',
                                    background: 'var(--accent-green)',
                                    color: 'var(--bg-page)',
                                    fontSize: '0.85rem',
                                    fontWeight: '500',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    boxShadow: '0 2px 8px rgba(76, 250, 116, 0.3)'
                                  }}>
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                      <polyline points="20 6 9 17 4 12"></polyline>
                                    </svg>
                                    {msg.text}
                                  </div>
                                </div>
                              );
                            }
                            
                            // Regular messages
                            return (
                              <div
                                key={idx}
                                style={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                  alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                                  gap: '0.25rem'
                                }}
                              >
                                <div style={{
                                  maxWidth: '75%',
                                  padding: '0.75rem 1rem',
                                  borderRadius: 'var(--radius-md)',
                                  background: msg.sender === 'user' 
                                    ? 'var(--accent-blue)' 
                                    : 'var(--bg-surface)',
                                  color: msg.sender === 'user' ? 'white' : 'var(--text-primary)',
                                  fontSize: '0.9rem',
                                  lineHeight: '1.5',
                                  wordBreak: 'break-word',
                                  whiteSpace: 'pre-wrap',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '0.5rem'
                                }}>
                                  {msg.isLoading ? (
                                    <>
                                      <div className="loader" style={{ width: '12px', height: '12px', borderWidth: '2px' }}></div>
                                      <span>Thinking...</span>
                                    </>
                                  ) : (
                                    msg.text
                                  )}
                                </div>
                                {!msg.isLoading && (
                                  <div style={{
                                    fontSize: '0.7rem',
                                    color: 'var(--text-tertiary)',
                                    padding: '0 0.5rem'
                                  }}>
                                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                  </div>
                                )}
                              </div>
                            );
                          })
                        )}
                        <div ref={chatEndRef} />
                      </div>

                      {/* Chat Input Area */}
                      <div style={{
                        borderTop: '1px solid var(--border-subtle)',
                        padding: '1rem',
                        display: 'flex',
                        gap: '0.75rem',
                        alignItems: 'flex-end'
                      }}>
                        <textarea
                          value={chatInput}
                          onChange={(e) => {
                            setChatInput(e.target.value);
                            // Auto-resize textarea
                            e.target.style.height = 'auto';
                            e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                          }}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                              e.preventDefault();
                              if (chatInput.trim()) {
                                handleSendChatMessage(chatInput.trim());
                                // Reset textarea height after sending
                                e.target.style.height = 'auto';
                              }
                            }
                          }}
                          placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                          style={{
                            flex: 1,
                            background: 'var(--bg-surface)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '0.75rem',
                            color: 'var(--text-primary)',
                            fontSize: '0.9rem',
                            fontFamily: 'inherit',
                            resize: 'none',
                            minHeight: '44px',
                            maxHeight: '120px',
                            lineHeight: '1.5',
                            overflowY: 'auto'
                          }}
                          rows={1}
                        />
                        <button
                          onClick={() => {
                            if (chatInput.trim()) {
                              handleSendChatMessage(chatInput.trim());
                            }
                          }}
                          disabled={!chatInput.trim()}
                          className="primary-btn"
                          style={{
                            padding: '0.75rem 1.5rem',
                            minWidth: '80px',
                            height: '44px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            opacity: chatInput.trim() ? 1 : 0.5,
                            cursor: chatInput.trim() ? 'pointer' : 'not-allowed'
                          }}
                        >
                          Send
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Redeem Credits Section */}
                  <div className="web-card">
                    <div className="input-group">
                      <label>Redeem Credits</label>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <input value={redeemCode} onChange={e => setRedeemCode(e.target.value)} placeholder="Code..." />
                        <button onClick={handleTopup} disabled={topupLoading} className="secondary-btn">Redeem</button>
                      </div>
                      {topupMessage && <small style={{ color: 'var(--accent-green)' }}>{topupMessage}</small>}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* --- VIEW: DATABASE OPS --- */}
          {activePage === 'dbopdb' && (
            <DatabaseOps />
          )}

          {/* --- VIEW: DASHBOARD (Make Thread) --- */}
          {activePage === 'dashboard' && (
            <div className="fade-in">
              {!isAuthenticated ? (
                <div style={{ textAlign: 'center', marginTop: '10vh' }}>
                  <h2>Welcome to NewsieAI</h2>
                  <p style={{ color: 'var(--text-secondary)', maxWidth: '400px', margin: '10px auto 30px' }}>
                    Your personal AI news assistant. Aggregate, filter, and summarize intelligence from the web and social media.
                  </p>
                  <button onClick={() => setActivePage('account')} className="primary-btn">Get Started</button>
                </div>
              ) : (
                <>
                  <div className="section-header">
                    <h2>Thread Configuration</h2>
                    <p>Customize how your AI agent gathers and processes information.</p>
                  </div>

                  {/* Load Threads Section */}
                  <div className="web-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ fontSize: '1rem' }}>My Thread List</h3>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Load your saved thread configurations.</p>
                      </div>
                      <button
                        onClick={(e) => handleLoadThreads(e)}
                        disabled={threadLoading}
                        className="secondary-btn"
                        style={{
                          padding: '8px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          minWidth: '36px'
                        }}
                        title="Refresh thread list"
                      >
                        <span
                          style={{
                            display: 'inline-block',
                            animation: threadLoading ? 'spin 1s linear infinite' : 'none'
                          }}
                        >
                          <Icons.Refresh />
                        </span>
                      </button>
                    </div>

                    <div style={{ marginTop: '1rem' }}>
                      <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem', display: 'block' }}>Select a thread:</label>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
                        {/* New Thread Button */}
                        <button
                          type="button"
                          onClick={handleCreateNewThread}
                          disabled={threadLoading}
                          className="secondary-btn"
                          style={{
                            textAlign: 'left',
                            padding: '0.75rem',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.5rem',
                            color: 'var(--text-secondary)',
                            borderStyle: 'dashed'
                          }}
                          title="Create New Thread"
                        >
                          <Icons.Plus />
                          <span>New Thread</span>
                        </button>

                        {threads.length > 0 && threads.map((thread) => (
                          <div
                            key={thread.thread_id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: '0.5rem',
                              padding: '0.5rem',
                              borderRadius: 'var(--radius-sm)',
                              background: selectedThread?.thread_id === thread.thread_id ? 'var(--bg-input)' : 'transparent'
                            }}
                          >
                            <button
                              type="button"
                              onClick={() => handleLoadThread(thread.thread_id)}
                              className={`secondary-btn ${selectedThread?.thread_id === thread.thread_id ? 'active' : ''}`}
                              style={{
                                textAlign: 'left',
                                padding: '0.75rem',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                flex: 1
                              }}
                            >
                              <span>{thread.name}</span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {/* Running Status Indicator */}
                                {thread.running ? (
                                  <span
                                    style={{
                                      display: 'inline-block',
                                      width: '8px',
                                      height: '8px',
                                      borderRadius: '50%',
                                      backgroundColor: 'var(--accent-green)',
                                      flexShrink: 0
                                    }}
                                    title="Running"
                                  />
                                ) : (
                                  <span
                                    style={{
                                      fontSize: '0.7rem',
                                      color: 'var(--text-secondary)',
                                      opacity: 0.6,
                                      fontWeight: '400'
                                    }}
                                  >
                                    stopped
                                  </span>
                                )}
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                  {new Date(thread.updated_at).toLocaleDateString()}
                                </span>
                              </div>
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setDeleteConfirmThread(thread);
                              }}
                              className="icon-btn-danger"
                              style={{
                                padding: '6px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'var(--accent-red)',
                                background: 'transparent',
                                border: '1px solid var(--accent-red)',
                                borderRadius: 'var(--radius-sm)',
                                cursor: 'pointer',
                                flexShrink: 0
                              }}
                              title="Delete thread"
                            >
                              <Icons.Trash />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Main Form */}
                  <div className="web-card">
                    <form onSubmit={(e) => {
                      e.preventDefault(); // Prevent default form submission - save is integrated into Load & Run
                    }} className="modern-form">

                      <div className="input-group">
                        <label>Thread Name</label>
                        <input
                          type="text"
                          value={threadName}
                          onChange={e => setThreadName(e.target.value)}
                          placeholder="My News Thread"
                          required
                        />
                      </div>

                      <div className="input-group">
                        <label>Time Zone</label>
                        <select
                          value={makeThreadData.timezone || 'UTC'}
                          onChange={e => setMakeThreadData({ ...makeThreadData, timezone: e.target.value })}
                          required
                        >
                          {Intl.supportedValuesOf('timeZone').map(tz => (
                            <option key={tz} value={tz}>
                              {tz.replace(/_/g, ' ')}
                            </option>
                          ))}
                        </select>
                        <small style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginTop: '0.25rem', display: 'block' }}>
                          Select your timezone for accurate notification scheduling
                        </small>
                      </div>

                      <div className="input-group">
                        <label>Notification Schedule</label>
                        <select
                          value={makeThreadData.notification_schedule.type}
                          onChange={e => {
                            const newType = e.target.value;
                            if (newType === 'daily') {
                              setMakeThreadData({
                                ...makeThreadData,
                                notification_schedule: { type: 'daily', times: makeThreadData.notification_schedule.times || [''] }
                              });
                            } else {
                              setMakeThreadData({
                                ...makeThreadData,
                                notification_schedule: {
                                  type: 'interval',
                                  interval: makeThreadData.notification_schedule.interval || 1,
                                  unit: makeThreadData.notification_schedule.unit || 'hours',
                                  startTime: makeThreadData.notification_schedule.startTime || ''
                                }
                              });
                            }
                          }}
                          style={{ marginBottom: '0.75rem' }}
                        >
                          <option value="daily">Everyday at specific time(s)</option>
                          <option value="interval">Once every X (time) starting from</option>
                        </select>

                        {makeThreadData.notification_schedule.type === 'daily' ? (
                          <div>
                            {makeThreadData.notification_schedule.times?.map((time, idx) => (
                              <div key={idx} style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem', alignItems: 'center' }}>
                                <input
                                  type="time"
                                  value={time}
                                  onChange={e => {
                                    const newTimes = [...makeThreadData.notification_schedule.times];
                                    newTimes[idx] = e.target.value;
                                    setMakeThreadData({
                                      ...makeThreadData,
                                      notification_schedule: { ...makeThreadData.notification_schedule, times: newTimes }
                                    });
                                  }}
                                  style={{ flex: 1 }}
                                />
                                {makeThreadData.notification_schedule.times.length > 1 && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      const newTimes = makeThreadData.notification_schedule.times.filter((_, i) => i !== idx);
                                      setMakeThreadData({
                                        ...makeThreadData,
                                        notification_schedule: { ...makeThreadData.notification_schedule, times: newTimes.length > 0 ? newTimes : [''] }
                                      });
                                    }}
                                    className="icon-btn-danger"
                                    style={{ padding: '4px 8px' }}
                                  >
                                    <Icons.Close />
                                  </button>
                                )}
                              </div>
                            ))}
                            <button
                              type="button"
                              onClick={() => {
                                setMakeThreadData({
                                  ...makeThreadData,
                                  notification_schedule: {
                                    ...makeThreadData.notification_schedule,
                                    times: [...makeThreadData.notification_schedule.times, '']
                                  }
                                });
                              }}
                              className="secondary-btn"
                              style={{ fontSize: '0.85rem', padding: '4px 8px', marginTop: '0.25rem' }}
                            >
                              <Icons.Plus /> Add Time
                            </button>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Once every</span>
                              <input
                                type="number"
                                min="1"
                                value={makeThreadData.notification_schedule.interval || 1}
                                onChange={e => {
                                  const interval = parseInt(e.target.value) || 1;
                                  setMakeThreadData({
                                    ...makeThreadData,
                                    notification_schedule: { ...makeThreadData.notification_schedule, interval }
                                  });
                                }}
                                style={{ width: '60px', textAlign: 'center' }}
                              />
                              <select
                                value={makeThreadData.notification_schedule.unit || 'hours'}
                                onChange={e => {
                                  setMakeThreadData({
                                    ...makeThreadData,
                                    notification_schedule: { ...makeThreadData.notification_schedule, unit: e.target.value }
                                  });
                                }}
                                style={{ width: '100px' }}
                              >
                                <option value="minutes">Minute(s)</option>
                                <option value="hours">Hour(s)</option>
                                <option value="days">Day(s)</option>
                              </select>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Starting from</span>
                              <input
                                type="time"
                                value={makeThreadData.notification_schedule.startTime || ''}
                                onChange={e => {
                                  setMakeThreadData({
                                    ...makeThreadData,
                                    notification_schedule: { ...makeThreadData.notification_schedule, startTime: e.target.value }
                                  });
                                }}
                                style={{ flex: 1 }}
                              />
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="input-group">
                        <label>Core Interests</label>
                        <textarea rows="2" value={makeThreadData.interests} onChange={e => setMakeThreadData({ ...makeThreadData, interests: e.target.value })} placeholder="Artificial Intelligence, Crypto Market, Macro Economics..." />
                      </div>

                      {/* Thread Blocks Builder */}
                      <div className="input-group">
                        <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          Execution Blocks
                          <button type="button" onClick={() => setShowBlockTypeMenu(!showBlockTypeMenu)} className="secondary-btn" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>+ Add Block</button>
                        </label>

                        {showBlockTypeMenu && (
                          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '8px', padding: '0.5rem', marginBottom: '1rem', display: 'flex', gap: '10px' }}>
                            {['general-search', 'x-from-user', 'x-from-topic'].map(type => {
                              // Set default method based on block type
                              const defaultMethod = type === 'x-from-user' ? 'newest' : 'selective';
                              return (
                                <button key={type} type="button" onClick={() => { setThreadBlocks([...threadBlocks, { id: Date.now(), type, tags: [], _inputValue: '', ai: defaultMethod }]); setShowBlockTypeMenu(false); }} className="secondary-btn" style={{ fontSize: '0.8rem' }}>
                                  {type.replace(/-/g, ' ')}
                                </button>
                              );
                            })}
                          </div>
                        )}

                        <div className="thread-builder">
                          {threadBlocks.length === 0 && (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No blocks added. Use the button above to define specific tasks.</div>
                          )}
                          {threadBlocks.map((block, idx) => (
                            <div key={block.id} className="thread-block">
                              <div className="block-header">
                                <span className="block-type-badge">{block.type}</span>
                                <button type="button" onClick={() => { const n = [...threadBlocks]; n.splice(idx, 1); setThreadBlocks(n); }} className="icon-btn-danger"><Icons.Close /></button>
                              </div>
                              <div className="form-grid-2">
                                {/* Tag Input Component */}
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                  {/* Input Field */}
                                  <input
                                    type="text"
                                    value={block._inputValue || ''}
                                    onChange={e => {
                                      const n = [...threadBlocks];
                                      n[idx]._inputValue = e.target.value;
                                      setThreadBlocks(n);
                                    }}
                                    onKeyDown={e => {
                                      if (e.key === 'Enter' && e.target.value.trim()) {
                                        e.preventDefault();
                                        const n = [...threadBlocks];
                                        const newTag = e.target.value.trim();
                                        if (!n[idx].tags) n[idx].tags = [];
                                        // Avoid duplicates
                                        if (!n[idx].tags.includes(newTag)) {
                                          n[idx].tags = [...n[idx].tags, newTag];
                                        }
                                        n[idx]._inputValue = '';
                                        setThreadBlocks(n);
                                      }
                                    }}
                                    placeholder={block.type.includes('user') ? 'Type @username and press Enter' : 'Type query and press Enter'}
                                    style={{ width: '100%' }}
                                  />
                                  {/* Tags Display */}
                                  <div style={{ 
                                    display: 'flex', 
                                    flexWrap: 'wrap', 
                                    gap: '0.5rem', 
                                    minHeight: '40px',
                                    padding: '0.5rem',
                                    background: 'var(--bg-input)',
                                    borderRadius: 'var(--radius-sm)',
                                    border: '1px solid var(--border-subtle)'
                                  }}>
                                    {/* Dummy sample tags */}
                                    {(!block.tags || block.tags.length === 0) && (
                                      <>
                                        <span style={{ 
                                          padding: '4px 8px', 
                                          background: 'var(--bg-surface)', 
                                          borderRadius: 'var(--radius-sm)',
                                          fontSize: '0.75rem',
                                          color: 'var(--text-secondary)',
                                          border: '1px dashed var(--border-subtle)'
                                        }}>sample-tag-1</span>
                                        <span style={{ 
                                          padding: '4px 8px', 
                                          background: 'var(--bg-surface)', 
                                          borderRadius: 'var(--radius-sm)',
                                          fontSize: '0.75rem',
                                          color: 'var(--text-secondary)',
                                          border: '1px dashed var(--border-subtle)'
                                        }}>sample-tag-2</span>
                                        <span style={{ 
                                          padding: '4px 8px', 
                                          background: 'var(--bg-surface)', 
                                          borderRadius: 'var(--radius-sm)',
                                          fontSize: '0.75rem',
                                          color: 'var(--text-secondary)',
                                          border: '1px dashed var(--border-subtle)'
                                        }}>sample-tag-3</span>
                                      </>
                                    )}
                                    {/* Actual tags */}
                                    {block.tags && block.tags.map((tag, tagIdx) => (
                                      <span
                                        key={tagIdx}
                                        style={{
                                          padding: '4px 8px',
                                          background: 'var(--accent-blue)',
                                          borderRadius: 'var(--radius-sm)',
                                          fontSize: '0.75rem',
                                          color: 'white',
                                          display: 'flex',
                                          alignItems: 'center',
                                          gap: '4px'
                                        }}
                                      >
                                        {tag}
                                        <button
                                          type="button"
                                          onClick={() => {
                                            const n = [...threadBlocks];
                                            n[idx].tags = n[idx].tags.filter((_, i) => i !== tagIdx);
                                            setThreadBlocks(n);
                                          }}
                                          style={{
                                            background: 'transparent',
                                            border: 'none',
                                            color: 'white',
                                            cursor: 'pointer',
                                            padding: '0',
                                            marginLeft: '4px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            width: '14px',
                                            height: '14px'
                                          }}
                                          title="Remove tag"
                                        >
                                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                        </button>
                                      </span>
                                    ))}
                                  </div>
                                </div>
                                <div
                                  className="method-selector-wrapper"
                                  style={{ position: 'relative' }}
                                  onMouseEnter={(e) => {
                                    const tooltip = e.currentTarget.querySelector('.method-tooltip');
                                    if (tooltip) tooltip.style.opacity = '1';
                                  }}
                                  onMouseLeave={(e) => {
                                    const tooltip = e.currentTarget.querySelector('.method-tooltip');
                                    if (tooltip) tooltip.style.opacity = '0';
                                  }}
                                >
                                  <select
                                    value={block.ai || (block.type === 'x-from-user' ? 'newest' : 'selective')}
                                    onChange={e => { const n = [...threadBlocks]; n[idx].ai = e.target.value; setThreadBlocks(n); }}
                                    style={{ width: '100%' }}
                                  >
                                    {block.type === 'x-from-user' ? (
                                      <>
                                        <option value="newest">Newest</option>
                                        <option value="summary">Summary</option>
                                      </>
                                    ) : (
                                      <>
                                        <option value="selective">Selective</option>
                                        <option value="newest">Newest</option>
                                        <option value="natural">Natural</option>
                                      </>
                                    )}
                                  </select>
                                  <div
                                    className="method-tooltip"
                                    style={{
                                      position: 'absolute',
                                      bottom: '100%',
                                      left: 0,
                                      marginBottom: '4px',
                                      padding: '6px 10px',
                                      background: 'var(--bg-surface)',
                                      border: '1px solid var(--border-subtle)',
                                      borderRadius: 'var(--radius-sm)',
                                      fontSize: '0.75rem',
                                      color: 'var(--text-secondary)',
                                      whiteSpace: 'nowrap',
                                      opacity: 0,
                                      pointerEvents: 'none',
                                      transition: 'opacity 0.2s',
                                      zIndex: 10,
                                      boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                                    }}
                                  >
                                    {block.type === 'x-from-user' ? (
                                      block.ai === 'newest' ? 'AI will present tweets that are most recent' :
                                        block.ai === 'summary' ? 'AI will present selective news based on profile' :
                                          'Select a method'
                                    ) : (
                                      block.ai === 'selective' ? 'AI will present selective news based on profile' :
                                        block.ai === 'newest' ? 'AI will present news that are most recent' :
                                          block.ai === 'natural' ? 'AI will present news based on trends' :
                                            'Select a method'
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Removed Save Thread button - integrated into Load & Run */}
                    </form>
                  </div>

                  {/* Dynamic Load & Run / Stop Running Button */}
                  {(selectedThread || threadName) && (
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                      {selectedThread?.running ? (
                        <button 
                          onClick={handleStopRunning} 
                          disabled={threadLoading} 
                          className="primary-btn" 
                          style={{ 
                            flex: 1, 
                            height: '50px', 
                            background: 'var(--accent-red)', 
                            borderColor: 'var(--accent-red)',
                            color: 'white'
                          }}
                        >
                          Stop Running
                        </button>
                      ) : (
                        <button 
                          onClick={handleLoadAndRun} 
                          disabled={threadLoading} 
                          className="primary-btn" 
                          style={{ 
                            flex: 1, 
                            height: '50px'
                          }}
                        >
                          Load & Run
                        </button>
                      )}
                    </div>
                  )}

                  {/* Delete Confirmation Popup */}
                  {deleteConfirmThread && (
                    <div
                      style={{
                        position: 'fixed',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'rgba(0, 0, 0, 0.5)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 1000
                      }}
                      onClick={() => setDeleteConfirmThread(null)}
                    >
                      <div
                        className="web-card"
                        style={{
                          maxWidth: '400px',
                          width: '90%',
                          padding: '1.5rem'
                        }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Confirm Deletion</h3>
                        <p style={{ marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
                          Are you sure you want to delete the thread <strong>"{deleteConfirmThread.name}"</strong>? This action cannot be undone.
                        </p>
                        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                          <button
                            onClick={() => setDeleteConfirmThread(null)}
                            className="secondary-btn"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleDeleteThread(deleteConfirmThread.thread_id, deleteConfirmThread.name)}
                            className="primary-btn"
                            style={{ background: 'var(--accent-red)', borderColor: 'var(--accent-red)' }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Status Messages */}
                  {message && (
                    <div className={`status-pill ${message.includes('Error') ? 'error' : 'success'}`} style={{ marginTop: '1.5rem' }}>
                      {message.includes('Error') ? <Icons.Alert /> : <Icons.Check />} {message}
                    </div>
                  )}

                  {/* Results Area */}
                  {(result?.items || result?.content) && (
                    <div className="fade-in" style={{ marginTop: '3rem' }}>
                      <div className="section-header">
                        <h2>Intelligence Feed</h2>
                        <p>Real-time results from your agent execution.</p>
                      </div>

                      {result.items && Array.isArray(result.items) ? (
                        <div className="news-grid">
                          {result.items.map((item, i) => (
                            <div key={i} className="news-card">
                              <div className="news-meta">
                                <span>{item.author ? `@${item.author}` : 'Web Source'}</span>
                                {item.url && <a href={item.url} target="_blank" className="news-link">Open Source ↗</a>}
                              </div>
                              <p style={{ fontSize: '0.95rem', lineHeight: '1.5', color: 'var(--text-primary)' }}>{item.text}</p>
                              {item.quoted_text && (
                                <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', borderLeft: '2px solid var(--border-subtle)' }}>
                                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Replying to @{item.quoted_author}</div>
                                  <p style={{ fontSize: '0.85rem', fontStyle: 'italic' }}>{item.quoted_text}</p>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <pre style={{ background: 'var(--bg-surface)', padding: '1.5rem', borderRadius: 'var(--radius-md)', overflowX: 'auto' }}>{JSON.stringify(result, null, 2)}</pre>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App