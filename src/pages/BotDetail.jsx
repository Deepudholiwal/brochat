import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, API_BASE } from '../utils/api';
import { ArrowLeft, Globe, Copy, Check, Trash2, Clock, CheckCircle, Loader, RotateCw } from 'lucide-react';

export default function BotDetail() {
  const { id } = useParams();
  const [bot, setBot] = useState(null);
  const [sources, setSources] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeTab, setActiveTab] = useState('knowledge');
  const [loading, setLoading] = useState(true);
  const [urlInput, setUrlInput] = useState('');
  const [copied, setCopied] = useState(false);
  const [refreshingSourceId, setRefreshingSourceId] = useState('');
  const [isAddingSource, setIsAddingSource] = useState(false);
  const [sourceError, setSourceError] = useState('');
  const hasScrapingSources = sources.some((source) => source.status === 'scraping');
  const isRefreshingSource = Boolean(refreshingSourceId);
  const pagesInProgress = sources
    .filter((source) => source.status === 'scraping')
    .reduce((total, source) => total + (source.pages_scraped || 0), 0);
  
  // Customization state
  const [editName, setEditName] = useState('');
  const [editWelcome, setEditWelcome] = useState('');
  const [editColor, setEditColor] = useState('');
  const themeColors = ['#c6ff6d', '#6dc6ff', '#ff6dc6', '#ffd76d', '#6dffc6'];

  const fetchData = async () => {
    try {
      const [botData, sourcesData, convsData] = await Promise.all([
        api.getBot(id),
        api.getSources(id),
        api.getConversations(id)
      ]);
      setBot(botData);
      setSources(sourcesData);
      setConversations(convsData);
      
      setEditName(botData.name);
      setEditWelcome(botData.welcome_message);
      setEditColor(botData.theme_color);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  useEffect(() => {
    if (!isAddingSource && !isRefreshingSource && !hasScrapingSources) return undefined;
    const interval = window.setInterval(() => {
      api.getSources(id).then(setSources).catch((err) => console.error(err));
    }, 1200);
    return () => window.clearInterval(interval);
  }, [id, isAddingSource, isRefreshingSource, hasScrapingSources]);

  const handleAddSource = async (e) => {
    e.preventDefault();
    if (!urlInput) return;
    setIsAddingSource(true);
    setSourceError('');
    try {
      await api.addSource(id, { url: urlInput });
      setUrlInput('');
      await fetchData();
    } catch (err) {
      setSourceError(err.message);
      api.getSources(id).then(setSources).catch((refreshError) => console.error(refreshError));
    } finally {
      setIsAddingSource(false);
    }
  };

  const handleDeleteSource = async (sourceId) => {
    try {
      await api.deleteSource(id, sourceId);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRefreshSource = async (sourceId) => {
    setRefreshingSourceId(sourceId);
    setSourceError('');
    try {
      await api.refreshSource(id, sourceId);
      await fetchData();
    } catch (err) {
      setSourceError(err.message);
      api.getSources(id).then(setSources).catch((refreshError) => console.error(refreshError));
    } finally {
      setRefreshingSourceId('');
    }
  };

  const handleSaveCustomize = async () => {
    try {
      await api.updateBot(id, {
        name: editName,
        welcome_message: editWelcome,
        theme_color: editColor
      });
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const copyEmbedCode = () => {
    const code = `<script src="${API_BASE}/widget.js" data-bot-id="${id}"></script>`;
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading || !bot) return <div className="loading-screen">Loading...</div>;

  return (
    <div className="bot-detail-layout">
      <header className="bot-detail-header glass-panel">
        <Link to="/dashboard" className="back-link"><ArrowLeft size={20} /> Back to Dashboard</Link>
        <div className="bot-title-area">
          <div className="bot-color-dot" style={{ backgroundColor: bot.theme_color }}></div>
          <h1>{bot.name}</h1>
        </div>
        
        <div className="tabs">
          {['knowledge', 'customize', 'embed', 'conversations'].map(tab => (
            <button 
              key={tab}
              className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </header>

      <main className="bot-detail-content">
        {activeTab === 'knowledge' && (
          <div className="tab-pane active slideIn">
            <div className="add-source-section glass-panel">
              <h3>Add Website URL</h3>
              <form onSubmit={handleAddSource} className="url-form">
                <Globe className="url-icon" size={20} />
                <input 
                  type="url" 
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://example.com"
                  disabled={isAddingSource}
                  required
                />
                <button type="submit" className="btn-primary" disabled={isAddingSource || hasScrapingSources}>
                  {isAddingSource || hasScrapingSources ? <><Loader size={16} className="pulse" /> Scraping{pagesInProgress ? ` · ${pagesInProgress} pages` : '...'}</> : <><Globe size={16} /> Scrape website</>}
                </button>
              </form>
              {(isAddingSource || isRefreshingSource || hasScrapingSources) && <div className="scrape-progress" role="status"><span />{pagesInProgress ? `${pagesInProgress} page${pagesInProgress === 1 ? '' : 's'} processed so far...` : 'Connecting to website and discovering pages...'}</div>}
              {sourceError && <p className="admin-error" role="alert">{sourceError}</p>}
            </div>

            <div className="sources-list glass-panel">
              <h3>Knowledge Sources</h3>
              {sources.length === 0 ? (
                <p className="empty-text">No sources added yet.</p>
              ) : (
                <ul className="source-items">
                  {sources.map(source => (
                    <li key={source.id} className="source-item">
                      <div className="source-info">
                        <span className="source-url">{source.url}</span>
                        <div className="source-meta">
                          <span className={`status-badge ${source.status}`}>
                            {source.status === 'pending' && <Clock size={12} />}
                            {source.status === 'scraping' && <Loader size={12} className="pulse" />}
                            {source.status === 'ready' && <CheckCircle size={12} />}
                            {source.status === 'scraping' ? 'Scraping' : source.status}
                          </span>
                          <span className="page-count">{source.status === 'scraping' ? `${source.pages_scraped || 0} processed` : `${source.pages_scraped || 0} pages`}</span>
                        </div>
                      </div>
                      <button
                        className="icon-btn"
                        title="Refresh website content and tool links"
                        aria-label={`Refresh ${source.url}`}
                        disabled={refreshingSourceId === source.id || source.status === 'scraping'}
                        onClick={() => handleRefreshSource(source.id)}
                      >
                        {refreshingSourceId === source.id ? <Loader className="pulse" size={17} /> : <RotateCw size={17} />}
                      </button>
                      <button className="icon-btn delete" aria-label={`Delete ${source.url}`} disabled={source.status === 'scraping'} onClick={() => handleDeleteSource(source.id)}>
                        <Trash2 size={18} />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}

        {activeTab === 'customize' && (
          <div className="tab-pane active slideIn customize-layout">
            <div className="customize-form glass-panel">
              <h3>Customize Bot</h3>
              <div className="form-group">
                <label>Bot Name</label>
                <input 
                  type="text" 
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Welcome Message</label>
                <textarea 
                  value={editWelcome}
                  onChange={(e) => setEditWelcome(e.target.value)}
                  rows="3"
                ></textarea>
              </div>
              <div className="form-group">
                <label>Theme Color</label>
                <div className="color-picker">
                  {themeColors.map(color => (
                    <button
                      key={color}
                      type="button"
                      className={`color-btn ${editColor === color ? 'active' : ''}`}
                      style={{ backgroundColor: color }}
                      onClick={() => setEditColor(color)}
                    />
                  ))}
                </div>
              </div>
              <button className="btn-primary" onClick={handleSaveCustomize}>Save Changes</button>
            </div>
            
            <div className="preview-section glass-panel">
              <h3>Live Preview</h3>
              <div className="widget-preview">
                <div className="widget-header" style={{ backgroundColor: editColor }}>
                  <h4>{editName}</h4>
                </div>
                <div className="widget-body">
                  <div className="message bot-message">{editWelcome}</div>
                </div>
                <div className="widget-input">
                  <input type="text" placeholder="Type a message..." disabled />
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'embed' && (
          <div className="tab-pane active slideIn">
            <div className="embed-section glass-panel">
              <h3>Embed Code</h3>
              <p>Add this code before the closing <code>&lt;/body&gt;</code> tag on your website.</p>
              
              <div className="code-block">
                <pre>
                  <code>
{`<script
  src="${API_BASE}/widget.js"
  data-bot-id="${id}"
></script>`}
                  </code>
                </pre>
                <button className="copy-btn" onClick={copyEmbedCode}>
                  {copied ? <Check size={18} /> : <Copy size={18} />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'conversations' && (
          <div className="tab-pane active slideIn">
            <div className="conversations-section glass-panel">
              <h3>Recent Conversations</h3>
              {conversations.length === 0 ? (
                <p className="empty-text">No conversations yet.</p>
              ) : (
                <div className="conv-list">
                  {conversations.map(conv => (
                    <div key={conv.id} className="conv-item">
                      <div className="conv-header">
                        <span className="visitor-id">Visitor: {conv.visitor_id.substring(0, 8)}...</span>
                        <span className="conv-date">{new Date(conv.created_at).toLocaleString()}</span>
                      </div>
                      <div className="conv-stats">
                        <span>{conv.messages_count} messages</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
