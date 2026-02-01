import { useState, useCallback, useRef, useEffect } from 'react'
import { auth } from './auth'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  MarkerType,
  Panel,
  Handle,
  Position,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './WorkflowStudio.css'

const API_BASE_URL = 'http://localhost:8008'

// SVG Icons for Nodes
const NodeIcons = {
  Time: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>,
  Source: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>,
  Agent: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect><circle cx="12" cy="5" r="2"></circle><path d="M12 7v4"></path><line x1="8" y1="16" x2="8" y2="16"></line><line x1="16" y1="16" x2="16" y2="16"></line></svg>,
  Delivery: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
}

// Node type definitions
const nodeTypes = {
  'notification-time': {
    label: 'Trigger Time',
    Icon: NodeIcons.Time,
    color: '#2962FF', // Tech Blue
    category: 'time',
    inputs: ['profile'],
    outputs: ['source'],
  },
  'info-source': {
    label: 'Info Source',
    Icon: NodeIcons.Source,
    color: '#00BFA5', // Teal
    category: 'source',
    inputs: ['time'],
    outputs: ['agent'],
  },
  'agent-behavior': {
    label: 'AI Agent',
    Icon: NodeIcons.Agent,
    color: '#7C4DFF', // Violet
    category: 'agent',
    inputs: ['source', 'agent'],
    outputs: ['delivery'],
  },
  'delivery-method': {
    label: 'Delivery',
    Icon: NodeIcons.Delivery,
    color: '#FF6D00', // Orange
    category: 'delivery',
    inputs: ['agent'],
    outputs: [],
  },
}

const initialNodes = []
const initialEdges = []

// Get node type by ID
const getNodeById = (nodes, id) => nodes.find((n) => n.id === id)
const getNodeTypeConfig = (type) => nodeTypes[type] || null

// Connection validation logic (Preserved)
const isValidConnection = (connection, nodes, edges) => {
  const sourceNode = getNodeById(nodes, connection.source)
  const targetNode = getNodeById(nodes, connection.target)
  if (!sourceNode || !targetNode) return false

  const sourceType = sourceNode.data.type
  const targetType = targetNode.data.type
  const sourceConfig = getNodeTypeConfig(sourceType)
  const targetConfig = getNodeTypeConfig(targetType)

  if (!sourceConfig || !targetConfig) return false

  const typeCategoryMap = {
    'notification-time': 'time',
    'info-source': 'source',
    'agent-behavior': 'agent',
    'delivery-method': 'delivery',
  }

  const sourceCategory = typeCategoryMap[sourceType]
  const targetCategory = typeCategoryMap[targetType]

  if (sourceCategory === 'time' && targetCategory === 'source') return true
  if (sourceCategory === 'source' && targetCategory === 'agent') return true
  if (sourceCategory === 'agent' && targetCategory === 'agent') return true
  if (sourceCategory === 'agent' && targetCategory === 'delivery') return true
  if (sourceCategory === 'delivery') return false
  if (targetCategory === 'agent') {
    const hasSourceInput = edges.some(
      (edge) =>
        edge.target === connection.target &&
        (getNodeById(nodes, edge.source)?.data.type === 'info-source' ||
          getNodeById(nodes, edge.source)?.data.type === 'agent-behavior')
    )
    if (sourceCategory === 'source' || sourceCategory === 'agent') return true
    return false
  }

  return false
}

// Reusable Header Component for Nodes
const NodeHeader = ({ config, label }) => (
  <div className="node-header" style={{ borderLeft: `3px solid ${config.color}` }}>
    <span className="node-icon" style={{ color: config.color }}><config.Icon /></span>
    <span className="node-label">{label}</span>
  </div>
)

const NotificationTimeNode = ({ data, selected, id }) => {
  const nodeConfig = nodeTypes['notification-time']
  return (
    <div className={`custom-node ${selected ? 'selected' : ''}`}>
      <NodeHeader config={nodeConfig} label={data.label || nodeConfig.label} />
      <div className="node-body">
        <div className="config-field">
          <label>Interval</label>
          <select
            value={data.config?.interval || 'Every X Hours'}
            onChange={(e) => data.onChange?.(id, { ...data.config, interval: e.target.value })}
            className="config-select"
          >
            <option value="Every X Hours">Every X Hours</option>
            <option value="Daily at Time">Daily at Time</option>
          </select>
        </div>
        {data.config?.interval === 'Every X Hours' ? (
          <>
            <div className="config-field">
              <label>Frequency (Hours)</label>
              <input
                type="number"
                min="1"
                value={data.config?.hours || data.config?.value || ''}
                onChange={(e) => data.onChange?.(id, { ...data.config, hours: e.target.value })}
                className="config-input"
              />
            </div>
            <div className="config-field">
              <label>Start From</label>
              <input
                type="time"
                value={data.config?.startTime || '09:00'}
                onChange={(e) => data.onChange?.(id, { ...data.config, startTime: e.target.value })}
                className="config-input"
              />
            </div>
          </>
        ) : (
          <div className="config-field">
            <label>Specific Time</label>
            <input
              type="time"
              value={data.config?.value || ''}
              onChange={(e) => data.onChange?.(id, { ...data.config, value: e.target.value })}
              className="config-input"
            />
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="react-flow__handle" style={{ background: nodeConfig.color }} />
    </div>
  )
}

const InfoSourceNode = ({ data, selected, id }) => {
  const nodeConfig = nodeTypes['info-source']
  return (
    <div className={`custom-node ${selected ? 'selected' : ''}`}>
      <NodeHeader config={nodeConfig} label={data.label || nodeConfig.label} />
      <div className="node-body">
        <div className="config-field">
          <label>Source Type</label>
          <select
            value={data.config?.type || 'Twitter User'}
            onChange={(e) => data.onChange?.(id, { ...data.config, type: e.target.value })}
            className="config-select"
          >
            <option value="Twitter User">Twitter User</option>
            <option value="General Search">General Search</option>
            <option value="Alpha Search">Alpha Search</option>
          </select>
        </div>
        <div className="config-field">
          <label>Query / Username</label>
          <input
            type="text"
            value={data.config?.value || ''}
            onChange={(e) => data.onChange?.(id, { ...data.config, value: e.target.value })}
            placeholder="@username or query"
            className="config-input"
          />
        </div>
      </div>
      <Handle type="target" position={Position.Left} className="react-flow__handle" style={{ background: nodeConfig.color }} />
      <Handle type="source" position={Position.Right} className="react-flow__handle" style={{ background: nodeConfig.color }} />
    </div>
  )
}

const AgentBehaviorNode = ({ data, selected, id }) => {
  const nodeConfig = nodeTypes['agent-behavior']
  return (
    <div className={`custom-node ${selected ? 'selected' : ''}`}>
      <NodeHeader config={nodeConfig} label={data.label || nodeConfig.label} />
      <div className="node-body">
        <div className="config-field">
          <label>Behavior</label>
          <select
            value={data.config?.behavior || 'None'}
            onChange={(e) => data.onChange?.(id, { ...data.config, behavior: e.target.value })}
            className="config-select"
          >
            <option value="None">None</option>
            <option value="Filter">Filter</option>
            <option value="Summary">Summary</option>
            <option value="Selective">Selective</option>
          </select>
        </div>
        <div className="config-field">
          <label>AI Model</label>
          <select
            value={data.config?.model || 'GPT-4o'}
            onChange={(e) => data.onChange?.(id, { ...data.config, model: e.target.value })}
            className="config-select"
            disabled={data.config?.behavior === 'None'}
          >
            <option value="GPT-4o">GPT-4o</option>
            <option value="Gemini Pro">Gemini Pro</option>
          </select>
        </div>
      </div>
      <Handle type="target" position={Position.Left} className="react-flow__handle" style={{ background: nodeConfig.color }} />
      <Handle type="source" position={Position.Right} className="react-flow__handle" style={{ background: nodeConfig.color }} />
    </div>
  )
}

const DeliveryMethodNode = ({ data, selected, id }) => {
  const nodeConfig = nodeTypes['delivery-method']
  return (
    <div className={`custom-node ${selected ? 'selected' : ''}`}>
      <NodeHeader config={nodeConfig} label={data.label || nodeConfig.label} />
      <div className="node-body">
        <div className="config-field">
          <label>Method</label>
          <select
            value={data.config?.method || 'Email'}
            onChange={(e) => data.onChange?.(id, { ...data.config, method: e.target.value })}
            className="config-select"
          >
            <option value="Email">Email</option>
            <option value="Display">Display</option>
          </select>
        </div>
        <div className="end-node-badge">TERMINAL NODE</div>
      </div>
      <Handle type="target" position={Position.Left} className="react-flow__handle" style={{ background: nodeConfig.color }} />
    </div>
  )
}

const nodeTypeConfig = {
  'notification-time': NotificationTimeNode,
  'info-source': InfoSourceNode,
  'agent-behavior': AgentBehaviorNode,
  'delivery-method': DeliveryMethodNode,
}

function WorkflowStudio() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNodeType, setSelectedNodeType] = useState(null)
  const [workflowName, setWorkflowName] = useState('New Strategy')
  const [currentWorkflowId, setCurrentWorkflowId] = useState(null)
  const [uploadStatus, setUploadStatus] = useState('')
  const [connectionError, setConnectionError] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [workflowList, setWorkflowList] = useState([])
  const [showWorkflowList, setShowWorkflowList] = useState(false)
  const reactFlowWrapper = useRef(null)
  const [reactFlowInstance, setReactFlowInstance] = useState(null)

  const updateNodeConfig = useCallback((nodeId, config) => {
    setNodes((nds) =>
      nds.map((node) => node.id === nodeId ? { ...node, data: { ...node.data, config } } : node)
    )
    if (selectedNodeType && selectedNodeType.id === nodeId) {
      setSelectedNodeType({ ...selectedNodeType, data: { ...selectedNodeType.data, config } })
    }
  }, [setNodes, selectedNodeType])

  const onConnect = useCallback((params) => {
    if (!isValidConnection(params, nodes, edges)) {
      setConnectionError('Invalid connection logic')
      setTimeout(() => setConnectionError(''), 3000)
      return
    }
    setEdges((eds) => addEdge({ ...params, type: 'smoothstep', animated: true, markerEnd: { type: MarkerType.ArrowClosed } }, eds))
    setConnectionError('')
  }, [setEdges, nodes, edges])

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback((event) => {
    event.preventDefault()
    const type = event.dataTransfer.getData('application/reactflow')
    if (!type || !reactFlowInstance) return

    const position = reactFlowInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY })
    const nodeConfig = nodeTypes[type]
    if (!nodeConfig) return

    const newNodeId = `${type}-${Date.now()}`
    let defaultConfig = {}
    if (type === 'notification-time') defaultConfig = { interval: 'Every X Hours', hours: '24', startTime: '09:00' }
    else if (type === 'info-source') defaultConfig = { type: 'Twitter User', value: '' }
    else if (type === 'agent-behavior') defaultConfig = { behavior: 'None', model: 'GPT-4o' }
    else if (type === 'delivery-method') defaultConfig = { method: 'Email' }

    const newNode = {
      id: newNodeId,
      type: type,
      position,
      data: {
        label: nodeConfig.label,
        type: type,
        config: defaultConfig,
        onChange: updateNodeConfig,
      },
      style: { background: 'transparent' }, // Styling handled by CSS classes
    }
    setNodes((nds) => nds.concat(newNode))
  }, [reactFlowInstance, setNodes, updateNodeConfig])

  const onNodeClick = useCallback((event, node) => setSelectedNodeType(node), [])
  const onPaneClick = useCallback(() => setSelectedNodeType(null), [])

  const validateWorkflow = useCallback(() => {
    const deliveryNodes = nodes.filter((n) => n.data.type === 'delivery-method')
    const nodesWithOutputs = nodes.filter((n) => n.data.type !== 'delivery-method' && !edges.some((e) => e.source === n.id))
    if (nodes.length > 0 && deliveryNodes.length === 0) return 'Workflow must end with a Delivery node'
    if (nodesWithOutputs.length > 0) return 'Some nodes are disconnected from output'
    return null
  }, [nodes, edges])

  const exportToJSON = useCallback(() => {
    const validationError = validateWorkflow()
    if (validationError) {
      setUploadStatus(`Warning: ${validationError}`)
      setTimeout(() => setUploadStatus(''), 5000)
      return
    }
    const workflowData = {
      name: workflowName,
      version: '1.0.0',
      nodes: nodes.map((node) => ({ id: node.id, type: node.data.type, label: node.data.label, position: node.position, config: node.data.config || {} })),
      edges: edges.map((edge) => ({ id: edge.id, source: edge.source, target: edge.target, type: edge.type })),
      createdAt: new Date().toISOString(),
    }
    const jsonString = JSON.stringify(workflowData, null, 2)
    const blob = new Blob([jsonString], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${workflowName.replace(/\s+/g, '_')}_workflow.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    setUploadStatus('Export successful')
    setTimeout(() => setUploadStatus(''), 3000)
  }, [nodes, edges, workflowName, validateWorkflow])

  const importFromJSON = useCallback((event) => {
    const file = event.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const workflowData = JSON.parse(e.target.result)
        if (workflowData.nodes && workflowData.edges) {
          setWorkflowName(workflowData.name || 'Imported')
          const importedNodes = workflowData.nodes.map((node) => ({
            ...node,
            data: { ...node, onChange: updateNodeConfig },
            style: { background: 'transparent' },
          }))
          setNodes(importedNodes)
          setEdges(workflowData.edges || [])
          setUploadStatus('Import successful')
        }
      } catch (error) { setUploadStatus('Import failed') }
      setTimeout(() => setUploadStatus(''), 3000)
    }
    reader.readAsText(file)
  }, [setNodes, setEdges, updateNodeConfig])

  const uploadToBackend = useCallback(async () => {
    const token = auth.getToken()
    if (!token) {
      setUploadStatus('Login required')
      return
    }
    const validationError = validateWorkflow()
    if (validationError) {
      setUploadStatus(`Warning: ${validationError}`)
      setTimeout(() => setUploadStatus(''), 5000)
      return
    }
    setIsUploading(true)
    setUploadStatus('')
    try {
      const workflowData = {
        workflow_id: currentWorkflowId,
        name: workflowName,
        version: '1.0.0',
        nodes: nodes.map((n) => ({ id: n.id, type: n.data.type, label: n.data.label, position: n.position, config: n.data.config || {} })),
        edges: edges.map((e) => ({ id: e.id, source: e.source, target: e.target, type: e.type })),
      }
      const response = await fetch(`${API_BASE_URL}/api/workflow/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...auth.getAuthHeader() },
        body: JSON.stringify(workflowData),
      })
      if (response.ok) {
        const data = await response.json()
        setCurrentWorkflowId(data.workflow_id)
        setUploadStatus('Saved to cloud')
        loadWorkflowList()
      } else {
        setUploadStatus('Save failed')
      }
    } catch (error) { setUploadStatus('Network error') }
    finally { setIsUploading(false); setTimeout(() => setUploadStatus(''), 5000); }
  }, [nodes, edges, workflowName, currentWorkflowId, validateWorkflow])

  const loadWorkflowList = useCallback(async () => {
    const token = auth.getToken()
    if (!token) return
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/workflow/list`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json', ...auth.getAuthHeader() },
      })
      if (response.ok) {
        const data = await response.json()
        setWorkflowList(data.workflows || [])
      }
    } catch (error) { console.error(error) }
    finally { setIsLoading(false) }
  }, [])

  const loadWorkflow = useCallback(async (workflowId) => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/workflow/${workflowId}`)
      if (response.ok) {
        const data = await response.json()
        const workflow = data.workflow
        if (workflow) {
          setWorkflowName(workflow.name)
          setCurrentWorkflowId(workflow.workflow_id)
          setNodes(workflow.nodes.map(n => ({ ...n, data: { ...n, onChange: updateNodeConfig }, style: { background: 'transparent' } })))
          setEdges(workflow.edges || [])
          setShowWorkflowList(false)
          setUploadStatus('Loaded')
        }
      }
    } catch (error) { setUploadStatus('Load failed') }
    finally { setIsLoading(false); setTimeout(() => setUploadStatus(''), 3000); }
  }, [setNodes, setEdges, updateNodeConfig])

  useEffect(() => {
    if (auth.isAuthenticated()) loadWorkflowList()
  }, [loadWorkflowList])

  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType)
    event.dataTransfer.effectAllowed = 'move'
  }

  if (!auth.isAuthenticated()) return <div className="workflow-studio"><div style={{ margin: 'auto' }}>Please login to access Studio</div></div>

  return (
    <div className="workflow-studio">
      <div className="workflow-toolbar">
        <input type="text" value={workflowName} onChange={(e) => setWorkflowName(e.target.value)} className="workflow-name-input" placeholder="Strategy Name" />
        <div className="toolbar-actions">
          <label className="toolbar-btn">
            Import
            <input type="file" accept=".json" onChange={importFromJSON} style={{ display: 'none' }} />
          </label>
          <button onClick={exportToJSON} className="toolbar-btn">Export</button>
          <button onClick={() => setShowWorkflowList(!showWorkflowList)} className="toolbar-btn">Strategies</button>
          <button onClick={uploadToBackend} disabled={isUploading} className="toolbar-btn upload-btn">
            {isUploading ? 'Saving...' : 'Save'}
          </button>
        </div>
        {uploadStatus && <div className="upload-status" style={{ position: 'absolute', top: '70px', left: '50%', transform: 'translateX(-50%)', background: '#fff', color: '#000', padding: '4px 12px', borderRadius: '100px', fontSize: '12px', zIndex: 100 }}>{uploadStatus}</div>}

        {showWorkflowList && (
          <div className="workflow-list-panel" style={{ position: 'absolute', top: '60px', right: '20px', background: '#18181b', border: '1px solid #27272a', padding: '1rem', borderRadius: '8px', zIndex: 100, width: '300px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem', borderBottom: '1px solid #27272a', paddingBottom: '0.5rem' }}>
              <h3 style={{ color: '#fff', margin: 0 }}>Saved Strategies</h3>
              <button onClick={() => setShowWorkflowList(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer' }}>✕</button>
            </div>
            {workflowList.map(w => (
              <div key={w.workflow_id} onClick={() => loadWorkflow(w.workflow_id)} style={{ padding: '0.5rem', borderBottom: '1px solid #27272a', cursor: 'pointer', color: '#a1a1aa', fontSize: '0.9rem' }}>
                {w.name}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="workflow-container">
        <div className="node-palette">
          <h3>Toolbox</h3>
          <div className="node-categories">
            {Object.entries(nodeTypes).map(([type, config]) => (
              <div key={type} className="palette-node" draggable onDragStart={(event) => onDragStart(event, type)}>
                <span className="palette-icon" style={{ color: config.color }}><config.Icon /></span>
                <span className="palette-label">{config.label}</span>
              </div>
            ))}
          </div>
          {selectedNodeType && (
            <div className="node-properties">
              <h4>Properties</h4>
              <div className="config-field">
                <label>Node Label</label>
                <input
                  type="text"
                  value={selectedNodeType.data.label || ''}
                  onChange={(e) => {
                    setNodes((nds) => nds.map((n) => n.id === selectedNodeType.id ? { ...n, data: { ...n.data, label: e.target.value } } : n))
                    setSelectedNodeType({ ...selectedNodeType, data: { ...selectedNodeType.data, label: e.target.value } })
                  }}
                />
              </div>
            </div>
          )}
        </div>

        <div className="react-flow-wrapper" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={nodeTypeConfig}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#27272a" gap={20} />
            <Controls />
            <MiniMap nodeColor="#52525b" maskColor="rgba(0,0,0,0.6)" />
          </ReactFlow>
        </div>
      </div>
    </div>
  )
}

export default WorkflowStudio