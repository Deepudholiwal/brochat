import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../utils/api';
import { ArrowLeft, Globe, Copy, Check, Trash2, Clock, CheckCircle, Loader } from 'lucide-react';

export default function BotDetail() {
  const { id } = useParams();
  const [bot, setBot] = useState(null);
  const [sources, setSources] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [activeTab, setActiveTab] = useState('knowledge');
  const [loading, setLoading] = useState(true);
  const [urlInput, setUrlInput] = useState('');
  const [copied, setCopied] = useState(false);
  
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

  const handleAddSource = async (e) => {
    e.preventDefault();
    if (!urlInput) return;
    try {
      await api.addSource(id, { url: urlInput });
      setUrlInput('');
      fetchData(); // Refresh sources
    } catch (err) {
      console.error(err);
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
    const code = `<script src="http://localhost:8000/widget.js" data-bot-id="${id}"></script>`;
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
                  required
                />
                <button type="submit" className="btn-primary">Scrape</button>
              </form>
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
                            {source.status}
                          </span>
                          <span className="page-count">{source.pages_scraped || 0} pages</span>
                        </div>
                      </div>
                      <button className="icon-btn delete" onClick={() => handleDeleteSource(source.id)}>
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
  src="http://localhost:8000/widget.js" 
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
