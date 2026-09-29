import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ArrowRight, Bot, Check, ChevronDown, Code2, Copy, FileText, Globe2, Menu, MessageCircle, Play, Send, ShieldCheck, Sparkles, X, Zap } from 'lucide-react';
import './styles.css';

import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import BotDetail from './pages/BotDetail';
import Admin from './pages/Admin';
import ProtectedRoute from './components/ProtectedRoute';
import { API_BASE } from './utils/api';

const embedCode = `<script>
  window.brochat = { botId: 'your-bot-id' };
</script>
<script async src="${API_BASE}/widget.js"></script>`;

function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [question, setQuestion] = useState('Can I add Brochat to my website?');
  const [messages, setMessages] = useState([{ role: 'bot', text: 'Absolutely. Add one small snippet to your website and Brochat is ready to help visitors.' }]);
  const navigate = useNavigate();

  function scrollTo(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
    setMenuOpen(false);
  }
  function sendQuestion(event) {
    event.preventDefault();
    const text = question.trim();
    if (!text) return;
    setMessages((current) => [...current, { role: 'user', text }, { role: 'bot', text: 'Yes. Brochat learns from your website, help center, and documents, then gives visitors answers in your own voice.' }]);
    setQuestion('');
  }
  async function copyCode() {
    try { await navigator.clipboard.writeText(embedCode); } catch { /* Preview browsers can block clipboard access. */ }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div className="site">
      <header className="site-header">
        <button className="brand" onClick={() => scrollTo('top')} aria-label="Brochat home"><span><MessageCircle size={20} /></span>brochat</button>
        <nav className={menuOpen ? 'nav-links open' : 'nav-links'}>
          <button onClick={() => scrollTo('how-it-works')}>How it works</button>
          <button onClick={() => scrollTo('features')}>Features</button>
          <button onClick={() => scrollTo('demo')}>Live demo</button>
          <button className="mobile-signin" onClick={() => navigate('/login')}>Sign in</button>
        </nav>
        <div className="header-actions">
          <button className="signin" onClick={() => navigate('/login')}>Sign in</button>
          <button className="header-cta" onClick={() => navigate('/signup')}>Create your bot <ArrowRight size={16} /></button>
          <button className="menu-toggle" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle navigation">{menuOpen ? <X size={22} /> : <Menu size={22} />}</button>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <p className="kicker"><Sparkles size={14} /> AI support that feels like you</p>
            <h1>Put your best answer on every page.</h1>
            <p className="hero-description">Brochat turns your website, help docs, and product knowledge into a helpful AI assistant your visitors can talk to anytime.</p>
            <div className="hero-actions">
              <button className="hero-cta" onClick={() => navigate('/signup')}>Build your free bot <ArrowRight size={18} /></button>
              <button className="demo-button" onClick={() => scrollTo('demo')}><span><Play size={13} fill="currentColor" /></span> See it in action</button>
            </div>
            <div className="trust-row"><span><Check size={14} /> Free to start</span><span><Check size={14} /> No credit card</span><span><Check size={14} /> Setup in minutes</span></div>
          </div>
          <div className="hero-visual" aria-label="Brochat chatbot preview">
            <div className="orbit orbit-one" /><div className="orbit orbit-two" />
            <div className="browser-preview">
              <div className="browser-bar"><span /><span /><span /><p>yourwebsite.com</p><i /></div>
              <div className="fake-site"><div className="fake-nav"><b>acme</b><em>Product   Pricing   Resources</em></div><div className="fake-page"><small>WELCOME TO ACME</small><strong>Better work starts here.</strong><span>Everything your team needs to get brilliant work done.</span><button>Get started</button></div></div>
            </div>
            <div className="chat-widget">
              <div className="widget-head"><span className="mini-logo"><Bot size={17} /></span><div><b>Bro at Acme</b><small><i /> Typically replies instantly</small></div><ChevronDown size={17} /></div>
              <div className="widget-body"><p className="chat-bubble">Hey there! How can I help you today?</p><p className="suggestion">What can I do with Acme?</p><p className="suggestion">Tell me about your plans</p></div>
              <div className="widget-input">Ask a question <Send size={16} /></div>
            </div>
          </div>
        </section>

        <section className="logo-strip"><p>Built for the people building what is next</p><div><b>northstar</b><b>hollow</b><b>FORM</b><b>ray</b><b>circuit</b></div></section>
        <section className="steps-section" id="how-it-works">
          <div className="section-intro"><p className="kicker dark-kicker">HOW IT WORKS</p><h2>Your knowledge. Their answers.<br />One simple flow.</h2></div>
          <div className="steps-grid">
            <Step number="01" icon={Globe2} title="Connect your content" text="Add your website, articles, guides, or files. Brochat understands the things you have already made." />
            <Step number="02" icon={Sparkles} title="Shape your assistant" text="Choose a name, tone, and style that feels at home in your product and with your customers." />
            <Step number="03" icon={Code2} title="Go live anywhere" text="Paste one embed code on the web, or add Brochat to your mobile app with the same helpful brain." />
          </div>
        </section>
        <section className="feature-section" id="features">
          <div className="feature-window">
            <div className="window-top"><span>brochat workspace</span><i>Live</i></div>
            <div className="workspace-body"><aside><span className="workspace-logo"><MessageCircle size={18} /></span><b>Overview</b><span>Knowledge</span><span>Conversations</span><span>Install widget</span></aside><div className="workspace-main"><p>KNOWLEDGE</p><h3>Everything your bot knows</h3><div className="source-card"><Globe2 size={18} /><span><b>acme.com</b><small>32 pages synced just now</small></span><Check size={17} /></div><div className="source-card"><FileText size={18} /><span><b>Product guide.pdf</b><small>Updated yesterday</small></span><Check size={17} /></div></div></div>
          </div>
          <div className="feature-copy"><p className="kicker dark-kicker">KNOWLEDGE THAT KEEPS UP</p><h2>A chatbot that knows your actual product.</h2><p>Brochat makes a living knowledge base from the places your team already maintains. New page? Updated article? It stays current.</p><ul><li><Check size={17} /> Crawl any public website</li><li><Check size={17} /> Upload documents and guides</li><li><Check size={17} /> Review answers and improve them</li></ul><button className="text-cta" onClick={() => navigate('/signup')}>Create a free workspace <ArrowRight size={16} /></button></div>
        </section>
        <section className="demo-section" id="demo">
          <div className="demo-copy"><p className="kicker">LIVE DEMO</p><h2>Ask Brochat a real question.</h2><p>This is the same friendly experience your visitors see on your website.</p><div className="answer-points"><span><ShieldCheck size={16} /> Answers grounded in your content</span><span><Zap size={16} /> Available every hour of every day</span></div></div>
          <div className="live-chat"><div className="live-chat-head"><span className="mini-logo"><Bot size={18} /></span><div><b>Brochat</b><small><i /> Online now</small></div></div><div className="live-chat-messages">{messages.slice(-4).map((message, index) => <div key={`${message.text}-${index}`} className={message.role === 'bot' ? 'live-message bot-answer' : 'live-message user-question'}>{message.text}</div>)}</div><form className="live-chat-input" onSubmit={sendQuestion}><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask Brochat anything..." /><button aria-label="Send message"><Send size={17} /></button></form></div>
        </section>
        <section className="final-cta"><span className="cta-spark"><Sparkles size={23} /></span><p className="kicker dark-kicker">READY WHEN YOU ARE</p><h2>Give every visitor a better way to ask.</h2><p>Make your product easier to understand, one useful conversation at a time.</p><button className="hero-cta" onClick={() => navigate('/signup')}>Create your free bot <ArrowRight size={18} /></button></section>
      </main>
      <footer><button className="brand" onClick={() => scrollTo('top')}><span><MessageCircle size={18} /></span>brochat</button><p>AI support for every curious visitor.</p><small>Copyright 2026 Brochat</small></footer>
      <button className="floating-code" onClick={copyCode} aria-label="Copy embed code"><Copy size={16} /> Embed</button>
      {copied && <span className="copy-toast">Embed code copied</span>}
    </div>
  );
}

function Step({ number, icon: Icon, title, text }) { return <article className="step"><span className="step-number">{number}</span><span className="step-icon"><Icon size={22} /></span><h3>{title}</h3><p>{text}</p></article>; }
function SignupModal({ onClose }) {
  const [submitted, setSubmitted] = useState(false);
  return <div className="modal-backdrop" onMouseDown={onClose}><form className="modal-card" onSubmit={(event) => { event.preventDefault(); setSubmitted(true); }} onMouseDown={(event) => event.stopPropagation()}>{submitted ? <div className="success"><span><Check size={26} /></span><h2>You are on the list.</h2><p>Your Brochat workspace is ready to be created. This demo stores no account data yet.</p><button className="modal-primary" type="button" onClick={onClose}>Done</button></div> : <><button className="modal-close" type="button" onClick={onClose} aria-label="Close"><X size={20} /></button><p className="kicker dark-kicker">GET STARTED FREE</p><h2>Meet your new support teammate.</h2><p>Set up your first Brochat assistant in a few minutes.</p><label>Work email<input type="email" required placeholder="you@company.com" /></label><label>Website<input type="url" required placeholder="https://yourwebsite.com" /></label><button className="modal-primary" type="submit">Create workspace <ArrowRight size={17} /></button><small>No credit card required.</small></>}</form></div>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/dashboard/bot/:id" element={<ProtectedRoute><BotDetail /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')).render(<App />);
