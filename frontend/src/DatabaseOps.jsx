import { useState, useEffect } from 'react'
import './App.css'

const API_BASE_URL = 'http://localhost:8008'

const Icons = {
  Database: () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>,
  Refresh: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>,
  Trash: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>,
  ChevronLeft: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6"></polyline></svg>,
  ChevronRight: () => <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="9 18 15 12 9 6"></polyline></svg>,
  Alert: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>,
  Close: () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>,
  Expand: () => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
}

function DatabaseOps() {
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState(null)
  const [tableData, setTableData] = useState(null)
  const [tableSchema, setTableSchema] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(100)
  const [orderBy, setOrderBy] = useState(null)
  const [orderDir, setOrderDir] = useState('ASC')
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [expandedContent, setExpandedContent] = useState(null) // { column, value, isJson }

  // Load tables on mount
  useEffect(() => {
    loadTables()
  }, [])

  // Load table data when table or page changes
  useEffect(() => {
    if (selectedTable) {
      loadTableData()
      loadTableSchema()
    }
  }, [selectedTable, page, limit, orderBy, orderDir])

  const loadTables = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/db/tables`)
      const data = await response.json()
      if (data.status === 'success') {
        setTables(data.tables || [])
        if (data.tables && data.tables.length > 0 && !selectedTable) {
          setSelectedTable(data.tables[0])
        }
      } else {
        setError('Failed to load tables')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const loadTableSchema = async () => {
    if (!selectedTable) return
    try {
      const response = await fetch(`${API_BASE_URL}/api/db/table/${selectedTable}/schema`)
      const data = await response.json()
      if (data.status === 'success') {
        setTableSchema(data)
      }
    } catch (err) {
      console.error('Error loading schema:', err)
    }
  }

  const loadTableData = async () => {
    if (!selectedTable) return
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString()
      })
      if (orderBy) {
        params.append('order_by', orderBy)
        params.append('order_dir', orderDir)
      }
      const response = await fetch(`${API_BASE_URL}/api/db/table/${selectedTable}/data?${params}`)
      const data = await response.json()
      if (data.status === 'success') {
        setTableData(data)
      } else {
        setError('Failed to load table data')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteRow = async (primaryKey, primaryKeyValue) => {
    if (!selectedTable) return
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({
        primary_key: primaryKey,
        primary_key_value: primaryKeyValue.toString()
      })
      const response = await fetch(`${API_BASE_URL}/api/db/table/${selectedTable}/row?${params}`, {
        method: 'DELETE'
      })
      const data = await response.json()
      if (data.status === 'success') {
        setDeleteConfirm(null)
        loadTableData() // Reload data
      } else {
        setError('Failed to delete row')
      }
    } catch (err) {
      setError(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const getPrimaryKey = () => {
    if (!tableSchema) return null
    const pkColumn = tableSchema.columns.find(col => col.pk)
    return pkColumn ? pkColumn.name : null
  }

  const handleSort = (column) => {
    if (orderBy === column) {
      setOrderDir(orderDir === 'ASC' ? 'DESC' : 'ASC')
    } else {
      setOrderBy(column)
      setOrderDir('ASC')
    }
    setPage(1) // Reset to first page
  }

  return (
    <div className="fade-in">
      <div className="section-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Icons.Database />
          <h2>Database Operations</h2>
        </div>
        <p>View and manage all database tables in the project</p>
      </div>

      {error && (
        <div className="status-pill error" style={{ marginBottom: '1rem' }}>
          <Icons.Alert /> {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '250px 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
        {/* Tables Sidebar */}
        <div className="web-card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: '600' }}>Tables</h3>
            <button
              onClick={loadTables}
              disabled={loading}
              className="secondary-btn"
              style={{ padding: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              title="Refresh tables"
            >
              <span style={{ display: 'inline-block', animation: loading ? 'spin 1s linear infinite' : 'none' }}>
                <Icons.Refresh />
              </span>
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '600px', overflowY: 'auto' }}>
            {tables.map((table) => (
              <button
                key={table}
                onClick={() => {
                  setSelectedTable(table)
                  setPage(1)
                  setOrderBy(null)
                  setOrderDir('ASC')
                }}
                className={`secondary-btn ${selectedTable === table ? 'active' : ''}`}
                style={{ textAlign: 'left', padding: '0.75rem' }}
              >
                {table}
              </button>
            ))}
          </div>
        </div>

        {/* Table Content */}
        <div>
          {selectedTable ? (
            <>
              {/* Table Info */}
              <div className="web-card" style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.25rem' }}>{selectedTable}</h3>
                    {tableData && (
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        {tableData.pagination.total} total rows
                      </p>
                    )}
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Limit:</label>
                    <select
                      value={limit}
                      onChange={(e) => {
                        setLimit(Number(e.target.value))
                        setPage(1)
                      }}
                      className="secondary-btn"
                      style={{ padding: '4px 8px', fontSize: '0.85rem' }}
                    >
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                      <option value={200}>200</option>
                      <option value={500}>500</option>
                    </select>
                  </div>
                </div>

                {/* Schema Info */}
                {tableSchema && (
                  <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
                    <strong style={{ color: 'var(--text-secondary)' }}>Columns: </strong>
                    {tableSchema.columns.map((col, idx) => (
                      <span key={col.name}>
                        {col.name} <span style={{ color: 'var(--text-secondary)' }}>({col.type})</span>
                        {col.pk && <span style={{ color: 'var(--accent-blue)', marginLeft: '4px' }}>PK</span>}
                        {idx < tableSchema.columns.length - 1 && ', '}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Table Data */}
              {loading && !tableData ? (
                <div className="web-card" style={{ textAlign: 'center', padding: '3rem' }}>
                  <div style={{ color: 'var(--text-secondary)' }}>Loading...</div>
                </div>
              ) : tableData && tableData.data ? (
                <div className="web-card">
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '2px solid var(--border-subtle)' }}>
                          {tableData.columns.map((col) => (
                            <th
                              key={col}
                              style={{
                                padding: '0.75rem',
                                textAlign: 'left',
                                fontWeight: '600',
                                color: 'var(--text-primary)',
                                cursor: 'pointer',
                                userSelect: 'none',
                                whiteSpace: 'nowrap'
                              }}
                              onClick={() => handleSort(col)}
                            >
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {col}
                                {orderBy === col && (
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                    {orderDir === 'ASC' ? '↑' : '↓'}
                                  </span>
                                )}
                              </div>
                            </th>
                          ))}
                          <th style={{ padding: '0.75rem', width: '60px' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {tableData.data.length === 0 ? (
                          <tr>
                            <td colSpan={tableData.columns.length + 1} style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
                              No data found
                            </td>
                          </tr>
                        ) : (
                          tableData.data.map((row, rowIdx) => (
                            <tr
                              key={rowIdx}
                              style={{
                                borderBottom: '1px solid var(--border-subtle)',
                                transition: 'background 0.2s'
                              }}
                              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-input)'}
                              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                            >
                              {tableData.columns.map((col) => {
                                const cellValue = row[col]
                                const isJson = Array.isArray(cellValue) || (typeof cellValue === 'object' && cellValue !== null)
                                const displayValue = isJson ? JSON.stringify(cellValue, null, 2) : (cellValue !== null && cellValue !== undefined ? String(cellValue) : null)
                                
                                return (
                                  <td 
                                    key={col} 
                                    style={{ 
                                      padding: '0.75rem', 
                                      maxWidth: '300px', 
                                      overflow: 'hidden',
                                      cursor: displayValue ? 'pointer' : 'default',
                                      position: 'relative'
                                    }}
                                    onClick={() => {
                                      if (displayValue) {
                                        setExpandedContent({
                                          column: col,
                                          value: cellValue,
                                          isJson: isJson,
                                          displayValue: displayValue
                                        })
                                      }
                                    }}
                                    title={displayValue ? 'Click to expand' : ''}
                                  >
                                    {isJson ? (
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <pre style={{ 
                                          margin: 0, 
                                          fontSize: '0.8rem', 
                                          whiteSpace: 'nowrap', 
                                          overflow: 'hidden', 
                                          textOverflow: 'ellipsis',
                                          maxWidth: 'calc(100% - 20px)',
                                          flex: 1
                                        }}>
                                          {displayValue}
                                        </pre>
                                        <Icons.Expand style={{ flexShrink: 0, opacity: 0.6, width: '14px', height: '14px' }} />
                                      </div>
                                    ) : (
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block', flex: 1 }}>
                                          {displayValue !== null ? displayValue : <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>null</span>}
                                        </span>
                                        {displayValue && (
                                          <Icons.Expand style={{ flexShrink: 0, opacity: 0.6, width: '14px', height: '14px' }} />
                                        )}
                                      </div>
                                    )}
                                  </td>
                                )
                              })}
                              <td style={{ padding: '0.75rem' }}>
                                <button
                                  onClick={() => {
                                    const pk = getPrimaryKey()
                                    if (pk && row[pk] !== undefined) {
                                      setDeleteConfirm({ primaryKey: pk, primaryKeyValue: row[pk], rowData: row })
                                    }
                                  }}
                                  className="icon-btn-danger"
                                  style={{
                                    padding: '4px 8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: 'var(--accent-red)',
                                    background: 'transparent',
                                    border: '1px solid var(--accent-red)',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: 'pointer'
                                  }}
                                  title="Delete row"
                                >
                                  <Icons.Trash />
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {tableData.pagination && tableData.pagination.pages > 1 && (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Page {tableData.pagination.page} of {tableData.pagination.pages}
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <button
                          onClick={() => setPage(p => Math.max(1, p - 1))}
                          disabled={tableData.pagination.page <= 1}
                          className="secondary-btn"
                          style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          <Icons.ChevronLeft /> Previous
                        </button>
                        <button
                          onClick={() => setPage(p => Math.min(tableData.pagination.pages, p + 1))}
                          disabled={tableData.pagination.page >= tableData.pagination.pages}
                          className="secondary-btn"
                          style={{ padding: '6px 12px', display: 'flex', alignItems: 'center', gap: '4px' }}
                        >
                          Next <Icons.ChevronRight />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="web-card" style={{ textAlign: 'center', padding: '3rem' }}>
                  <div style={{ color: 'var(--text-secondary)' }}>No data available</div>
                </div>
              )}
            </>
          ) : (
            <div className="web-card" style={{ textAlign: 'center', padding: '3rem' }}>
              <div style={{ color: 'var(--text-secondary)' }}>Select a table to view data</div>
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
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
          onClick={() => setDeleteConfirm(null)}
        >
          <div
            className="web-card"
            style={{
              maxWidth: '500px',
              width: '90%',
              padding: '1.5rem'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem' }}>Confirm Deletion</h3>
            <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
              Are you sure you want to delete this row from <strong>{selectedTable}</strong>?
            </p>
            <div style={{ marginBottom: '1.5rem', padding: '0.75rem', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem' }}>
              <strong>{deleteConfirm.primaryKey}:</strong> {deleteConfirm.primaryKeyValue}
            </div>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="secondary-btn"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteRow(deleteConfirm.primaryKey, deleteConfirm.primaryKeyValue)}
                className="primary-btn"
                style={{ background: 'var(--accent-red)', borderColor: 'var(--accent-red)' }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Expanded Content Modal */}
      {expandedContent && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1001,
            padding: '2rem'
          }}
          onClick={() => setExpandedContent(null)}
        >
          <div
            className="web-card"
            style={{
              maxWidth: '90vw',
              maxHeight: '90vh',
              width: '800px',
              padding: '1.5rem',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.25rem' }}>
                  {expandedContent.column}
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  {expandedContent.isJson ? 'JSON Data' : 'Text Content'}
                </p>
              </div>
              <button
                onClick={() => setExpandedContent(null)}
                className="secondary-btn"
                style={{
                  padding: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  minWidth: '32px',
                  minHeight: '32px'
                }}
                title="Close"
              >
                <Icons.Close />
              </button>
            </div>
            
            <div
              style={{
                flex: 1,
                overflow: 'auto',
                background: 'var(--bg-input)',
                borderRadius: 'var(--radius-sm)',
                padding: '1rem',
                border: '1px solid var(--border-subtle)'
              }}
            >
              {expandedContent.isJson ? (
                <pre
                  style={{
                    margin: 0,
                    fontSize: '0.85rem',
                    lineHeight: '1.6',
                    color: 'var(--text-primary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'
                  }}
                >
                  {expandedContent.displayValue}
                </pre>
              ) : (
                <div
                  style={{
                    fontSize: '0.9rem',
                    lineHeight: '1.6',
                    color: 'var(--text-primary)',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}
                >
                  {expandedContent.displayValue}
                </div>
              )}
            </div>
            
            <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                onClick={() => {
                  if (expandedContent.isJson) {
                    navigator.clipboard.writeText(expandedContent.displayValue)
                  } else {
                    navigator.clipboard.writeText(String(expandedContent.displayValue))
                  }
                }}
                className="secondary-btn"
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
              >
                Copy to Clipboard
              </button>
              <button
                onClick={() => setExpandedContent(null)}
                className="primary-btn"
                style={{ padding: '6px 12px', fontSize: '0.85rem' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DatabaseOps

