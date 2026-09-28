import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, logout } from '../utils/api';
import { Bot, MessageSquare, Link as LinkIcon, Plus, LogOut, X } from 'lucide-react';

export default function Dashboard() {
  const [bots, setBots] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  
  // Modal state
  const [newBotName, setNewBotName] = useState('');
  const [newBotWelcome, setNewBotWelcome] = useState('Hi! How can I help you today?');
  const [newBotColor, setNewBotColor] = useState('#c6ff6d');
  
  const navigate = useNavigate();
  const themeColors = ['#c6ff6d', '#6dc6ff', '#ff6dc6', '#ffd76d', '#6dffc6'];

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [userData, botsData] = await Promise.all([
          api.me(),
          api.getBots()
        ]);
        setUser(userData);
        setBots(botsData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleCreateBot = async (e) => {
    e.preventDefault();
    try {
      const newBot = await api.createBot({
        name: newBotName,
        theme_color: newBotColor,
        welcome_message: newBotWelcome
      });
      setBots([...bots, newBot]);
      setIsModalOpen(false);
      setNewBotName('');
    } catch (err) {
      console.error(err);
    }
  };

  const totalConversations = bots.reduce((acc, bot) => acc + (bot.conversations_count || 0), 0);
  const activeSources = bots.reduce((acc, bot) => acc + (bot.sources_count || 0), 0);

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div className="sidebar-header">
          <h2>BroChat</h2>
        </div>
        <nav className="sidebar-nav">
          <a href="#" className="active"><Bot size={20} /> My Bots</a>
          <a href="#"><LinkIcon size={20} /> Settings</a>
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">
            <span>{user?.name}</span>
            <button onClick={logout} className="logout-btn"><LogOut size={16} /></button>
          </div>
        </div>
      </aside>
      
      <main className="dashboard-content">
        <header className="content-header">
          <h1>My Bots</h1>
          <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={18} /> Create New Bot
          </button>
        </header>

        <section className="stats-row">
          <div className="stat-card glass-panel">
            <div className="stat-icon"><Bot size={24} /></div>
            <div className="stat-info">
              <h3>{bots.length}</h3>
              <p>Total Bots</p>
            </div>
          </div>
          <div className="stat-card glass-panel">
            <div className="stat-icon"><MessageSquare size={24} /></div>
            <div className="stat-info">
              <h3>{totalConversations}</h3>
              <p>Conversations</p>
            </div>
          </div>
          <div className="stat-card glass-panel">
            <div className="stat-icon"><LinkIcon size={24} /></div>
            <div className="stat-info">
              <h3>{activeSources}</h3>
              <p>Active Sources</p>
            </div>
          </div>
        </section>

        <section className="bot-grid">
          {bots.length === 0 ? (
            <div className="empty-state glass-panel">
              <Bot size={48} className="empty-icon" />
              <h3>No bots yet</h3>
              <p>Create your first AI assistant to get started.</p>
              <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
                Create your first bot
              </button>
            </div>
          ) : (
            bots.map(bot => (
              <div 
                key={bot.id} 
                className="bot-card glass-panel"
                onClick={() => navigate(`/dashboard/bot/${bot.id}`)}
              >
                <div className="bot-card-header">
                  <div className="bot-color-dot" style={{ backgroundColor: bot.theme_color }}></div>
                  <h3>{bot.name}</h3>
                </div>
                <div className="bot-card-stats">
                  <span>{bot.sources_count || 0} Sources</span>
                  <span>Created {new Date(bot.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))
          )}
        </section>
      </main>

      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content glass-panel">
            <div className="modal-header">
              <h2>Create New Bot</h2>
              <button className="close-btn" onClick={() => setIsModalOpen(false)}><X size={20} /></button>
            </div>
            <form onSubmit={handleCreateBot}>
              <div className="form-group">
                <label>Bot Name</label>
                <input 
                  type="text" 
                  value={newBotName} 
                  onChange={(e) => setNewBotName(e.target.value)}
                  required 
                  placeholder="e.g. Support Assistant"
                />
              </div>
              <div className="form-group">
                <label>Welcome Message</label>
                <textarea 
                  value={newBotWelcome}
                  onChange={(e) => setNewBotWelcome(e.target.value)}
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
                      className={`color-btn ${newBotColor === color ? 'active' : ''}`}
                      style={{ backgroundColor: color }}
                      onClick={() => setNewBotColor(color)}
                    />
                  ))}
                </div>
              </div>
              <button type="submit" className="btn-primary full-width">Create Bot</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
