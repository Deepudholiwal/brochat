import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ArrowRightLeft, LogOut, Save, ShieldCheck, Trash2, Upload } from 'lucide-react';
import { api, logout } from '../utils/api';

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [bots, setBots] = useState([]);
  const [selectedBotId, setSelectedBotId] = useState('');
  const [botDraft, setBotDraft] = useState(null);
  const [password, setPassword] = useState('');
  const [backupFile, setBackupFile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const selectedUser = users.find((user) => user.id === selectedUserId);
  const selectedBot = bots.find((bot) => bot.id === selectedBotId);

  useEffect(() => {
    let active = true;
    api.getAdminUsers()
      .then((data) => {
        if (!active) return;
        setUsers(data);
        setSelectedUserId(data[0]?.id || '');
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedUserId) {
      setBots([]);
      setSelectedBotId('');
      return undefined;
    }

    let active = true;
    setBots([]);
    setSelectedBotId('');
    setBotDraft(null);
    api.getAdminUserBots(selectedUserId)
      .then((data) => {
        if (!active) return;
        setBots(data);
        setSelectedBotId(data[0]?.id || '');
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => { active = false; };
  }, [selectedUserId]);

  useEffect(() => {
    if (selectedBot) {
      setBotDraft({
        name: selectedBot.name,
        welcome_message: selectedBot.welcome_message,
        theme_color: selectedBot.theme_color || '#c6ff6d',
      });
    } else {
      setBotDraft(null);
    }
  }, [selectedBotId, bots]);

  async function handlePasswordReset(event) {
    event.preventDefault();
    if (!selectedUser || password.length < 12) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      await api.resetAdminUserPassword(selectedUser.id, password);
      setPassword('');
      setNotice(`Password updated for ${selectedUser.email}.`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleBotSave(event) {
    event.preventDefault();
    if (!selectedBot || !botDraft) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const updated = await api.updateAdminBot(selectedBot.id, botDraft);
      setBots((current) => current.map((bot) => bot.id === updated.id ? { ...bot, ...updated } : bot));
      setNotice('Bot settings saved.');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleBotTransfer() {
    if (!selectedBot || !selectedUser || selectedUser.role === 'admin') return;
    const confirmed = window.confirm(
      `Move "${selectedBot.name}" from ${selectedUser.email} to your administrator account? The bot ID and knowledge will stay the same.`
    );
    if (!confirmed) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await api.transferAdminBotToSelf(selectedBot.id);
      const updatedUsers = await api.getAdminUsers();
      setUsers(updatedUsers);
      setSelectedUserId(result.user_id);
      setNotice('Bot moved to your administrator account. Its ID and embed code are unchanged.');
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteUser(user) {
    if (user.role === 'admin') return;
    const confirmed = window.confirm(
      `Permanently delete ${user.name} (${user.email})? This also permanently deletes ${user.bot_count} bot(s), their website sources, conversations, and indexed knowledge. This cannot be undone.`
    );
    if (!confirmed) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const result = await api.deleteAdminUser(user.id);
      const remainingUsers = users.filter((item) => item.id !== user.id);
      setUsers(remainingUsers);
      if (selectedUserId === user.id) setSelectedUserId(remainingUsers[0]?.id || '');
      setNotice(`Account permanently deleted with ${result.deleted_bots} bot(s).`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleBackupRestore(event) {
    event.preventDefault();
    if (!backupFile) return;
    setSaving(true);
    setError('');
    setNotice('');
    try {
      const backup = JSON.parse(await backupFile.text());
      const result = await api.restoreAdminBackup(backup);
      const counts = result.restored;
      setNotice(`Merged ${counts.users} accounts, ${counts.bots} bots, ${counts.sources} sources, ${counts.conversations} conversations, and ${counts.vector_documents} knowledge records.`);
      setBackupFile(null);
      const input = event.currentTarget.querySelector('input[type="file"]');
      if (input) input.value = '';
      const updatedUsers = await api.getAdminUsers();
      setUsers(updatedUsers);
      if (selectedUserId && updatedUsers.some((user) => user.id === selectedUserId)) {
        setSelectedUserId(selectedUserId);
      } else {
        setSelectedUserId(updatedUsers[0]?.id || '');
      }
    } catch (requestError) {
      setError(requestError instanceof SyntaxError ? 'The selected file is not valid JSON.' : requestError.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dashboard-layout">
      <aside className="dashboard-sidebar">
        <div className="sidebar-header"><h2>BroChat</h2></div>
        <nav className="sidebar-nav">
          <Link to="/dashboard"><ArrowLeft size={18} /> Workspace</Link>
          <Link to="/admin" className="active"><ShieldCheck size={18} /> Administration</Link>
        </nav>
        <div className="sidebar-footer">
          <div className="user-info">
            <span>Administrator</span>
            <button onClick={logout} className="logout-btn" aria-label="Sign out"><LogOut size={16} /></button>
          </div>
        </div>
      </aside>

      <main className="dashboard-content">
        <header className="admin-header">
          <div>
            <h1>Account administration</h1>
            <p>Review user accounts, reset passwords, and manage bot settings.</p>
          </div>
          <span className="admin-count">{users.length} accounts</span>
        </header>

        <section className="admin-restore-panel glass-panel">
          <div>
            <h2>Restore a local backup</h2>
            <p>Merge accounts, bots, conversations, and website knowledge. Existing hosted records are kept.</p>
          </div>
          <form onSubmit={handleBackupRestore}>
            <input type="file" accept=".json,application/json" aria-label="BroChat backup JSON file" onChange={(event) => setBackupFile(event.target.files?.[0] || null)} required />
            <button className="btn-primary" type="submit" disabled={!backupFile || saving}><Upload size={16} /> {saving ? 'Restoring...' : 'Merge backup'}</button>
          </form>
          <small>Backup files contain account password hashes. Upload only over this secure admin page.</small>
          {error && !selectedUser && <p className="admin-error" role="alert">{error}</p>}
          {notice && <p className="admin-notice" role="status">{notice}</p>}
        </section>

        {loading ? <div className="loading-screen">Loading accounts...</div> : (
          <div className="admin-workspace">
            <section className="admin-panel glass-panel" aria-labelledby="admin-accounts-heading">
              <div className="admin-panel-heading">
                <h2 id="admin-accounts-heading">Accounts</h2>
                <span className="admin-count">{users.length}</span>
              </div>
              {users.length ? (
                <div className="admin-account-list">
                  {users.map((user) => (
                    <div className="admin-account-row" key={user.id}>
                      <button
                        className={`admin-account${user.id === selectedUserId ? ' selected' : ''}`}
                        onClick={() => { setSelectedUserId(user.id); setError(''); setNotice(''); }}
                      >
                        <span className="admin-account-name">
                          {user.name || 'Unnamed account'}
                          <span className="admin-role">{user.role}</span>
                        </span>
                        <span className="admin-account-email">{user.email}</span>
                        <span className="admin-account-meta">{user.bot_count} bots</span>
                      </button>
                      {user.role !== 'admin' && (
                        <button
                          className="admin-delete-user"
                          title={`Permanently delete ${user.email} and their bots`}
                          aria-label={`Permanently delete ${user.email}`}
                          disabled={saving}
                          onClick={() => handleDeleteUser(user)}
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : <p className="admin-empty">No accounts found.</p>}
            </section>

            <section className="admin-panel glass-panel" aria-label="Selected account management">
              {!selectedUser ? (
                <div className="admin-empty">{error || 'Select an account to view its bots and manage access.'}</div>
              ) : (
                <div className="admin-detail-stack">
                  <div className="admin-selected-user">
                    <h3>{selectedUser.name}</h3>
                    <p>{selectedUser.email}</p>
                    <form className="admin-reset-form" onSubmit={handlePasswordReset}>
                      <input
                        aria-label="New account password"
                        type="password"
                        autoComplete="new-password"
                        minLength={12}
                        maxLength={128}
                        placeholder="New password (12+ characters)"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        required
                      />
                      <button type="submit" disabled={saving || password.length < 12}>Set password</button>
                    </form>
                  </div>

                  <div>
                    <div className="admin-panel-heading">
                      <h2>Chatbots</h2>
                      <span className="admin-count">{bots.length}</span>
                    </div>
                    {bots.length ? (
                      <div className="admin-bot-list">
                        {bots.map((bot) => (
                          <button
                            key={bot.id}
                            className={`admin-bot-item${bot.id === selectedBotId ? ' selected' : ''}`}
                            onClick={() => setSelectedBotId(bot.id)}
                          >
                            <span><strong>{bot.name}</strong><small>{bot.source_count} sources · {bot.conversation_count} conversations</small></span>
                            <span className="bot-color-dot" style={{ backgroundColor: bot.theme_color }} />
                          </button>
                        ))}
                      </div>
                    ) : <p className="admin-empty">This account has no chatbots.</p>}
                  </div>

                  {botDraft && (
                    <form className="admin-bot-form" onSubmit={handleBotSave}>
                      <h3>Edit chatbot</h3>
                      <label>Bot name<input maxLength={120} value={botDraft.name} onChange={(event) => setBotDraft({ ...botDraft, name: event.target.value })} required /></label>
                      <label>Welcome message<textarea maxLength={2000} rows={3} value={botDraft.welcome_message} onChange={(event) => setBotDraft({ ...botDraft, welcome_message: event.target.value })} required /></label>
                      <label>Theme color<input type="color" value={botDraft.theme_color} onChange={(event) => setBotDraft({ ...botDraft, theme_color: event.target.value })} /></label>
                      {selectedUser.role !== 'admin' && <button type="button" className="admin-transfer-bot" disabled={saving} onClick={handleBotTransfer}><ArrowRightLeft size={15} /> Move bot to my admin account</button>}
                      <button type="submit" disabled={saving}><Save size={15} /> Save bot settings</button>
                    </form>
                  )}
                </div>
              )}
              {error && selectedUser && <p className="admin-error" role="alert">{error}</p>}
              {notice && <p className="admin-notice" role="status">{notice}</p>}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}