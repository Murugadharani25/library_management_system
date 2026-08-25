import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import axios from 'axios';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import {
  BookOpen, LayoutDashboard, Users, ArrowLeftRight, LogOut,
  Plus, Search, Trash2, Settings, Edit, X, Clock, AlertTriangle,
  BookMarked, Calendar, IndianRupee, History, GraduationCap, User,
  Send, CheckCircle, XCircle, FileText, Library
} from 'lucide-react';
import './styles.css';

const API = 'http://127.0.0.1:8000/api';
const api = axios.create({ baseURL: API });
api.interceptors.request.use(c => {
  const t = localStorage.getItem('token');
  if (t) c.headers.Authorization = `Bearer ${t}`;
  return c;
});

/* ============================================================
   LOGIN PAGE
   ============================================================ */
function Login({ onLogin }) {
  const [email, setEmail] = useState('admin@library.com');
  const [password, setPassword] = useState('admin123');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async e => {
    e.preventDefault();
    setLoading(true);
    setErr('');
    try {
      const r = await api.post('/auth/login/', { email, password });
      localStorage.setItem('token', r.data.token);
      localStorage.setItem('user', JSON.stringify(r.data.user));
      onLogin(r.data.user);
    } catch (e) {
      setErr(e.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login">
      <div className="login-card">
        <div className="logo"><BookOpen /> Smart Library</div>
        <h1>Welcome back</h1>
        <p>Manage your library in one place.</p>
        {err && <div className="error">{err}</div>}
        <form onSubmit={submit}>
          <label>Email<input value={email} onChange={e => setEmail(e.target.value)} /></label>
          <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
          <button disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
        </form>
        <div className="credentials-hint">
          <small><strong>Demo Credentials:</strong></small>
          <small>Admin: admin@library.com / admin123</small>
          <small>Student: student@library.com / student123</small>
          <small>Teacher: teacher@library.com / teacher123</small>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   MAIN APP - ROLE-BASED ROUTING
   ============================================================ */
function App() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('user') || 'null'));
  const navigate = useNavigate();

  const logout = () => {
    localStorage.clear();
    setUser(null);
    navigate('/');
  };

  const handleLogin = (u) => {
    setUser(u);
    if (u.role === 'admin') navigate('/admin/dashboard');
    else if (u.role === 'student') navigate('/student/dashboard');
    else if (u.role === 'teacher') navigate('/teacher/dashboard');
  };

  if (!user) return <Login onLogin={handleLogin} />;

  return (
    <Routes>
      {/* Admin Routes */}
      {user.role === 'admin' && (
        <>
          <Route path="/admin/dashboard" element={<AdminLayout user={user} logout={logout} tab="dashboard"><AdminDashboard /></AdminLayout>} />
          <Route path="/admin/books" element={<AdminLayout user={user} logout={logout} tab="books"><AdminBooks user={user} /></AdminLayout>} />
          <Route path="/admin/members" element={<AdminLayout user={user} logout={logout} tab="members"><AdminMembers /></AdminLayout>} />
          <Route path="/admin/transactions" element={<AdminLayout user={user} logout={logout} tab="transactions"><AdminTransactions /></AdminLayout>} />
          <Route path="/admin/book-requests" element={<AdminLayout user={user} logout={logout} tab="book-requests"><AdminBookRequests /></AdminLayout>} />
          <Route path="/admin/settings" element={<AdminLayout user={user} logout={logout} tab="settings"><AdminSettings /></AdminLayout>} />
          <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
        </>
      )}

      {/* Student Routes */}
      {user.role === 'student' && (
        <>
          <Route path="/student/dashboard" element={<PersonalLayout user={user} logout={logout}><PersonalDashboard user={user} /></PersonalLayout>} />
          <Route path="*" element={<Navigate to="/student/dashboard" replace />} />
        </>
      )}

      {/* Teacher Routes */}
      {user.role === 'teacher' && (
        <>
          <Route path="/teacher/dashboard" element={<PersonalLayout user={user} logout={logout}><PersonalDashboard user={user} /></PersonalLayout>} />
          <Route path="*" element={<Navigate to="/teacher/dashboard" replace />} />
        </>
      )}
    </Routes>
  );
}

/* ============================================================
   ADMIN LAYOUT (Sidebar + Content)
   ============================================================ */
function AdminLayout({ user, logout, tab, children }) {
  const navigate = useNavigate();

  const navItems = [
    ['dashboard', 'Dashboard', LayoutDashboard, '/admin/dashboard'],
    ['books', 'Books', BookOpen, '/admin/books'],
    ['members', 'Members', Users, '/admin/members'],
    ['transactions', 'Transactions', ArrowLeftRight, '/admin/transactions'],
    ['book-requests', 'Book Requests', FileText, '/admin/book-requests'],
    ['settings', 'Settings', Settings, '/admin/settings'],
  ];

  return (
    <div className="app">
      <aside>
        <div className="brand"><BookOpen /> Smart Library</div>
        <div className="nav">
          {navItems.map(([id, label, Icon, path]) => (
            <button key={id} className={tab === id ? 'active' : ''} onClick={() => navigate(path)}>
              <Icon size={18} />{label}
            </button>
          ))}
        </div>
        <button className="logout" onClick={logout}><LogOut size={18} />Logout</button>
      </aside>
      <main>
        <header>
          <div>
            <h2>{tab === 'book-requests' ? 'Book Requests' : tab[0].toUpperCase() + tab.slice(1)}</h2>
            <span>Welcome, {user.name}</span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

/* ============================================================
   PERSONAL LAYOUT (Student / Teacher)
   ============================================================ */
function PersonalLayout({ user, logout, children }) {
  return (
    <div className="app">
      <aside>
        <div className="brand"><BookOpen /> Smart Library</div>
        <div className="nav">
          <button className="active">
            <LayoutDashboard size={18} />Dashboard
          </button>
        </div>
        <button className="logout" onClick={logout}><LogOut size={18} />Logout</button>
      </aside>
      <main>
        <header>
          <div>
            <h2>My Dashboard</h2>
            <span>Welcome, {user.name} <span className="role-badge">{user.role}</span></span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

/* ============================================================
   ADMIN DASHBOARD
   ============================================================ */
function AdminDashboard() {
  const [data, setData] = useState({});
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/dashboard/').then(r => setData(r.data)).catch(() => {});
  }, []);

  return (
    <>
      <div className="stats">
        {[
          ['Total Books', data.total_books, '📚'],
          ['Available', data.available_books, '✅'],
          ['Issued', data.issued_books, '📖'],
          ['Members', data.members, '👥'],
          ['Overdue', data.overdue, '⚠️'],
          ['Pending Requests', data.pending_requests, '📋'],
          ['Fines Collected', `₹${data.pending_fines || 0}`, '💰'],
        ].map(([label, value, icon]) => (
          <div className="stat" key={label}>
            <span>{icon} {label}</span>
            <strong>{value ?? 0}</strong>
          </div>
        ))}
      </div>
      <section className="panel">
        <h3>Quick Actions</h3>
        <div className="actions">
          <button onClick={() => navigate('/admin/books')}><BookOpen /> Manage Books</button>
          <button onClick={() => navigate('/admin/book-requests')}><FileText /> Book Requests</button>
          <button onClick={() => navigate('/admin/transactions')}><ArrowLeftRight /> Transactions</button>
          <button onClick={() => navigate('/admin/members')}><Users /> Members</button>
          <button onClick={() => navigate('/admin/settings')}><Settings /> Settings</button>
        </div>
      </section>
    </>
  );
}

/* ============================================================
   PERSONAL DASHBOARD (Student / Teacher) - ENHANCED
   ============================================================ */
function PersonalDashboard({ user }) {
  const [dashData, setDashData] = useState(null);
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [requestingId, setRequestingId] = useState(null);
  const [tab, setTab] = useState('overview');

  const loadAll = async () => {
    setLoading(true);
    try {
      const [d, b] = await Promise.all([
        api.get('/my-dashboard/'),
        api.get('/books/'),
      ]);
      setDashData(d.data);
      setBooks(b.data.books);
    } catch (e) {}
    setLoading(false);
  };

  useEffect(() => { loadAll(); }, []);

  const requestBook = async (bookId) => {
    setRequestingId(bookId);
    try {
      await api.post(`/books/${bookId}/request/`);
      await loadAll();
    } catch (e) {
      alert(e.response?.data?.detail || 'Request failed');
    } finally {
      setRequestingId(null);
    }
  };

  if (loading) return <div className="panel"><p>Loading your dashboard...</p></div>;
  if (!dashData) return <div className="panel"><p>Unable to load dashboard data.</p></div>;

  const {
    issued_books = [], history = [], my_requests = [],
    total_fine_pending = 0, total_fine_paid = 0,
    total_books = 0, total_available = 0,
    my_issued_count = 0, pending_returns = 0, my_pending_requests = 0,
  } = dashData;

  // Build a set of book IDs that have pending requests (to disable button)
  const pendingRequestBookIds = new Set(
    my_requests.filter(r => r.status === 'Pending').map(r => r.book_id)
  );
  const issuedBookIds = new Set(
    issued_books.map(b => {
      // Extract book_id from the issued book - we need to find it
      return null; // We'll use a different approach
    })
  );

  const filteredBooks = books.filter(b =>
    [b.title, b.author, b.isbn, b.category].join(' ').toLowerCase().includes(q.toLowerCase())
  );

  const tabs = [
    ['overview', 'Overview'],
    ['all-books', 'All Library Books'],
    ['my-issued', 'My Issued Books'],
    ['my-requests', 'My Requests'],
    ['history', 'Borrowing History'],
  ];

  return (
    <>
      {/* Stats */}
      <div className="stats stats-personal-wide">
        <div className="stat">
          <span>📚 Total Books</span>
          <strong>{total_books}</strong>
        </div>
        <div className="stat">
          <span>✅ Available</span>
          <strong>{total_available}</strong>
        </div>
        <div className="stat">
          <span><BookMarked size={16} /> My Issued</span>
          <strong>{my_issued_count}</strong>
        </div>
        <div className="stat">
          <span><Clock size={16} /> Pending Returns</span>
          <strong>{pending_returns}</strong>
        </div>
        <div className="stat">
          <span><FileText size={16} /> My Requests</span>
          <strong>{my_pending_requests}</strong>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="dash-tabs">
        {tabs.map(([id, label]) => (
          <button key={id} className={`dash-tab ${tab === id ? 'dash-tab-active' : ''}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {tab === 'overview' && (
        <>
          {total_fine_pending > 0 && (
            <div className="fine-alert">
              <AlertTriangle size={18} /> You have a pending fine of <strong>₹{total_fine_pending}</strong>
            </div>
          )}
          <section className="panel">
            <h3><BookMarked size={18} /> Currently Issued Books</h3>
            {issued_books.length === 0 ? (
              <p className="empty-msg">No books currently issued to you.</p>
            ) : (
              <div className="tablewrap">
                <table>
                  <thead>
                    <tr><th>Book</th><th>Issue Date</th><th>Due Date</th><th>Late Days</th><th>Fine</th></tr>
                  </thead>
                  <tbody>
                    {issued_books.map(b => (
                      <tr key={b.id} className={b.late_days > 0 ? 'overdue-row' : ''}>
                        <td><b>{b.book_title}</b>{b.book_author && <><br /><small>{b.book_author}</small></>}</td>
                        <td>{new Date(b.issue_date).toLocaleDateString()}</td>
                        <td>
                          {new Date(b.due_date).toLocaleDateString()}
                          {b.late_days > 0 && <span className="pill pill-danger"> Overdue</span>}
                        </td>
                        <td>{b.late_days > 0 ? b.late_days : '—'}</td>
                        <td className={b.fine > 0 ? 'fine-amount' : ''}>₹{b.fine}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {my_requests.filter(r => r.status === 'Pending').length > 0 && (
            <section className="panel">
              <h3><FileText size={18} /> Pending Requests</h3>
              <div className="tablewrap">
                <table>
                  <thead><tr><th>Book</th><th>Requested Date</th><th>Status</th></tr></thead>
                  <tbody>
                    {my_requests.filter(r => r.status === 'Pending').map(r => (
                      <tr key={r.id}>
                        <td><b>{r.book_title}</b>{r.book_author && <><br /><small>{r.book_author}</small></>}</td>
                        <td>{new Date(r.requested_at).toLocaleDateString()}</td>
                        <td><span className="pill pill-pending">{r.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}

      {/* All Library Books Tab */}
      {tab === 'all-books' && (
        <section className="panel">
          <div className="toolbar">
            <div className="search">
              <Search size={17} />
              <input placeholder="Search title, author, ISBN, category..." value={q} onChange={e => setQ(e.target.value)} />
            </div>
          </div>
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>Book</th>
                  <th>Author</th>
                  <th>Category</th>
                  <th>Total</th>
                  <th>Available</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredBooks.map(b => {
                  const hasPending = pendingRequestBookIds.has(b.id);
                  const isAvailable = b.available_copies > 0;
                  return (
                    <tr key={b.id}>
                      <td>
                        <b>{b.title}</b><br />
                        <small>{b.publisher || ''} · {b.year || ''}</small>
                      </td>
                      <td>{b.author}</td>
                      <td><span className="pill">{b.category}</span></td>
                      <td>{b.total_copies}</td>
                      <td>{b.available_copies}</td>
                      <td>
                        <span className={`pill ${isAvailable ? 'pill-available' : 'pill-danger'}`}>
                          {isAvailable ? 'Available' : 'Unavailable'}
                        </span>
                      </td>
                      <td>
                        {hasPending ? (
                          <span className="pill pill-pending">Request Pending</span>
                        ) : (
                          <button
                            className="small request-btn"
                            disabled={requestingId === b.id}
                            onClick={() => requestBook(b.id)}
                          >
                            <Send size={14} />
                            {requestingId === b.id ? 'Requesting...' : 'Request Book'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* My Issued Books Tab */}
      {tab === 'my-issued' && (
        <section className="panel">
          <h3><BookMarked size={18} /> My Issued Books</h3>
          {issued_books.length === 0 ? (
            <p className="empty-msg">No books currently issued to you.</p>
          ) : (
            <div className="tablewrap">
              <table>
                <thead>
                  <tr><th>Book</th><th>Issue Date</th><th>Due Date</th><th>Status</th><th>Fine</th></tr>
                </thead>
                <tbody>
                  {issued_books.map(b => (
                    <tr key={b.id} className={b.late_days > 0 ? 'overdue-row' : ''}>
                      <td><b>{b.book_title}</b>{b.book_author && <><br /><small>{b.book_author}</small></>}</td>
                      <td>{new Date(b.issue_date).toLocaleDateString()}</td>
                      <td>
                        {new Date(b.due_date).toLocaleDateString()}
                        {b.late_days > 0 && <span className="pill pill-danger"> Overdue</span>}
                      </td>
                      <td><span className="pill">Issued</span></td>
                      <td className={b.fine > 0 ? 'fine-amount' : ''}>₹{b.fine}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* My Requests Tab */}
      {tab === 'my-requests' && (
        <section className="panel">
          <h3><FileText size={18} /> My Book Requests</h3>
          {my_requests.length === 0 ? (
            <p className="empty-msg">No book requests yet. Browse "All Library Books" to request one.</p>
          ) : (
            <div className="tablewrap">
              <table>
                <thead>
                  <tr><th>Book</th><th>Requested Date</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {my_requests.map(r => (
                    <tr key={r.id}>
                      <td><b>{r.book_title}</b>{r.book_author && <><br /><small>{r.book_author}</small></>}</td>
                      <td>{new Date(r.requested_at).toLocaleDateString()}</td>
                      <td>
                        <span className={`pill ${r.status === 'Pending' ? 'pill-pending' : r.status === 'Issued' ? 'pill-issued' : 'pill-danger'}`}>
                          {r.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {/* Borrowing History Tab */}
      {tab === 'history' && (
        <section className="panel">
          <h3><History size={18} /> Borrowing History</h3>
          {history.length === 0 ? (
            <p className="empty-msg">No borrowing history yet.</p>
          ) : (
            <div className="tablewrap">
              <table>
                <thead>
                  <tr><th>Book</th><th>Issue Date</th><th>Due Date</th><th>Return Date</th><th>Fine</th></tr>
                </thead>
                <tbody>
                  {history.map(h => (
                    <tr key={h.id}>
                      <td><b>{h.book_title}</b>{h.book_author && <><br /><small>{h.book_author}</small></>}</td>
                      <td>{new Date(h.issue_date).toLocaleDateString()}</td>
                      <td>{new Date(h.due_date).toLocaleDateString()}</td>
                      <td>{new Date(h.return_date).toLocaleDateString()}</td>
                      <td className={h.fine > 0 ? 'fine-amount' : ''}>₹{h.fine}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}

/* ============================================================
   ADMIN BOOKS
   ============================================================ */
function AdminBooks({ user }) {
  const [books, setBooks] = useState([]);
  const [members, setMembers] = useState([]);
  const [q, setQ] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [editBook, setEditBook] = useState(null);
  const [showIssue, setShowIssue] = useState(null);

  const load = async () => {
    const [b, m] = await Promise.all([api.get('/books/'), api.get('/members/')]);
    setBooks(b.data.books);
    setMembers(m.data.members);
  };

  useEffect(() => { load(); }, []);

  const del = async id => {
    if (confirm('Delete this book?')) {
      await api.delete(`/books/${id}/`);
      load();
    }
  };

  const filtered = books.filter(b =>
    [b.title, b.author, b.isbn, b.category].join(' ').toLowerCase().includes(q.toLowerCase())
  );

  return (
    <section className="panel">
      <div className="toolbar">
        <div className="search">
          <Search size={17} />
          <input placeholder="Search title, author, ISBN..." value={q} onChange={e => setQ(e.target.value)} />
        </div>
        <button onClick={() => setShowAdd(true)}><Plus size={17} /> Add Book</button>
      </div>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>Book</th>
              <th>Author</th>
              <th>Category</th>
              <th>ISBN</th>
              <th>Available</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(b => (
              <tr key={b.id}>
                <td>
                  <b>{b.title}</b><br />
                  <small>{b.publisher || ''} · {b.year || ''}</small>
                </td>
                <td>{b.author}</td>
                <td><span className="pill">{b.category}</span></td>
                <td>{b.isbn}</td>
                <td>{b.available_copies}/{b.total_copies}</td>
                <td className="action-cell">
                  <button className="small" disabled={!b.available_copies} onClick={() => setShowIssue(b)}>Issue</button>
                  <button className="small secondary" onClick={() => setEditBook(b)}><Edit size={14} /></button>
                  <button className="icon" onClick={() => del(b.id)}><Trash2 size={16} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showAdd && <AddBook close={() => setShowAdd(false)} done={load} />}
      {editBook && <EditBookModal book={editBook} close={() => setEditBook(null)} done={load} />}
      {showIssue && <IssueBookModal book={showIssue} members={members} close={() => setShowIssue(null)} done={load} />}
    </section>
  );
}

/* ============================================================
   ADD BOOK MODAL
   ============================================================ */
function AddBook({ close, done }) {
  const [f, setF] = useState({
    title: '', author: '', isbn: '', category: 'Programming',
    publisher: '', year: 2026, total_copies: 1, shelf: ''
  });
  const ch = e => setF({ ...f, [e.target.name]: e.target.value });
  const save = async e => {
    e.preventDefault();
    await api.post('/books/', {
      ...f, total_copies: Number(f.total_copies),
      available_copies: Number(f.total_copies), year: Number(f.year)
    });
    close(); done();
  };

  return (
    <div className="modal">
      <form className="modal-card" onSubmit={save}>
        <div className="modal-header">
          <h3>Add New Book</h3>
          <button type="button" className="icon" onClick={close}><X size={18} /></button>
        </div>
        {['title', 'author', 'isbn', 'category', 'publisher', 'year', 'total_copies', 'shelf'].map(k => (
          <input key={k} required={['title', 'author', 'isbn', 'category'].includes(k)} name={k}
            placeholder={k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            value={f[k]} onChange={ch} />
        ))}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>Cancel</button>
          <button>Add Book</button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
   EDIT BOOK MODAL
   ============================================================ */
function EditBookModal({ book, close, done }) {
  const [f, setF] = useState({
    title: book.title || '', author: book.author || '', isbn: book.isbn || '',
    category: book.category || '', publisher: book.publisher || '',
    year: book.year || 2026, total_copies: book.total_copies || 1, shelf: book.shelf || ''
  });
  const ch = e => setF({ ...f, [e.target.name]: e.target.value });
  const save = async e => {
    e.preventDefault();
    await api.put(`/books/${book.id}/`, {
      ...f, total_copies: Number(f.total_copies), year: Number(f.year)
    });
    close(); done();
  };

  return (
    <div className="modal">
      <form className="modal-card" onSubmit={save}>
        <div className="modal-header">
          <h3>Edit Book</h3>
          <button type="button" className="icon" onClick={close}><X size={18} /></button>
        </div>
        {['title', 'author', 'isbn', 'category', 'publisher', 'year', 'total_copies', 'shelf'].map(k => (
          <input key={k} required={['title', 'author', 'isbn', 'category'].includes(k)} name={k}
            placeholder={k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            value={f[k]} onChange={ch} />
        ))}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>Cancel</button>
          <button>Save Changes</button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
   ISSUE BOOK MODAL
   ============================================================ */
function IssueBookModal({ book, members, close, done }) {
  const [memberId, setMemberId] = useState('');
  const [err, setErr] = useState('');

  const issue = async e => {
    e.preventDefault();
    if (!memberId) { setErr('Please select a member'); return; }
    try {
      await api.post('/transactions/issue/', { book_id: book.id, member_id: memberId });
      close(); done();
    } catch (e) {
      setErr(e.response?.data?.detail || 'Issue failed');
    }
  };

  return (
    <div className="modal">
      <form className="modal-card" onSubmit={issue}>
        <div className="modal-header">
          <h3>Issue Book</h3>
          <button type="button" className="icon" onClick={close}><X size={18} /></button>
        </div>
        <p><strong>Book:</strong> {book.title}</p>
        {err && <div className="error">{err}</div>}
        <label>
          Select Member
          <select value={memberId} onChange={e => setMemberId(e.target.value)} className="form-select">
            <option value="">-- Choose Member --</option>
            {members.map(m => (
              <option key={m.id} value={m.id}>{m.name} ({m.role || 'member'}) — {m.email}</option>
            ))}
          </select>
        </label>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>Cancel</button>
          <button>Issue Book</button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
   ADMIN MEMBERS
   ============================================================ */
function AdminMembers() {
  const [members, setMembers] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [createdInfo, setCreatedInfo] = useState(null);

  const load = async () => {
    const r = await api.get('/members/');
    setMembers(r.data.members);
  };

  useEffect(() => { load(); }, []);

  return (
    <>
      <section className="panel">
        <div className="toolbar">
          <h3 style={{ margin: 0 }}>All Members</h3>
          <button onClick={() => { setShowAdd(true); setCreatedInfo(null); }}><Plus size={17} /> Add Member</button>
        </div>

        {createdInfo && (
          <div className="success-banner">
            ✅ Member created! Login credentials — Email: <strong>{createdInfo.email}</strong>, Password: <strong>{createdInfo.default_password}</strong>
          </div>
        )}

        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Phone</th>
                <th>Role</th>
                <th>Department</th>
                <th>Year</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {members.map(m => (
                <tr key={m.id}>
                  <td><b>{m.name}</b></td>
                  <td>{m.email}</td>
                  <td>{m.phone}</td>
                  <td><span className={`pill ${m.role === 'teacher' ? 'pill-teacher' : 'pill-student'}`}>{m.role || 'student'}</span></td>
                  <td>{m.department}</td>
                  <td>{m.year}</td>
                  <td><span className={`pill ${m.status === 'Active' ? '' : 'pill-inactive'}`}>{m.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {showAdd && <AddMember close={() => setShowAdd(false)} done={load} onCreated={setCreatedInfo} />}
    </>
  );
}

/* ============================================================
   ADD MEMBER MODAL
   ============================================================ */
function AddMember({ close, done, onCreated }) {
  const [f, setF] = useState({
    name: '', email: '', phone: '', role: 'student',
    department: '', year: '', status: 'Active'
  });
  const [err, setErr] = useState('');

  const ch = e => setF({ ...f, [e.target.name]: e.target.value });

  const save = async e => {
    e.preventDefault();
    setErr('');
    try {
      const r = await api.post('/members/', f);
      if (r.data.default_password) {
        onCreated({ email: r.data.email, default_password: r.data.default_password });
      }
      close(); done();
    } catch (e) {
      setErr(e.response?.data?.detail || 'Failed to create member');
    }
  };

  return (
    <div className="modal">
      <form className="modal-card" onSubmit={save}>
        <div className="modal-header">
          <h3>Add New Member</h3>
          <button type="button" className="icon" onClick={close}><X size={18} /></button>
        </div>
        {err && <div className="error">{err}</div>}
        <input required name="name" placeholder="Full Name" value={f.name} onChange={ch} />
        <input required name="email" placeholder="Email" type="email" value={f.email} onChange={ch} />
        <input name="phone" placeholder="Phone Number" value={f.phone} onChange={ch} />
        <label>
          Role
          <select name="role" value={f.role} onChange={ch} className="form-select">
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
          </select>
        </label>
        <input name="department" placeholder="Department" value={f.department} onChange={ch} />
        <input name="year" placeholder="Year (e.g. 1, 2, 3)" value={f.year} onChange={ch} />
        <label>
          Status
          <select name="status" value={f.status} onChange={ch} className="form-select">
            <option value="Active">Active</option>
            <option value="Inactive">Inactive</option>
          </select>
        </label>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={close}>Cancel</button>
          <button>Create Member</button>
        </div>
      </form>
    </div>
  );
}

/* ============================================================
   ADMIN TRANSACTIONS
   ============================================================ */
function AdminTransactions() {
  const [tx, setTx] = useState([]);

  const load = async () => {
    const r = await api.get('/transactions/');
    setTx(r.data.transactions);
  };

  useEffect(() => { load(); }, []);

  const ret = async id => {
    try {
      const r = await api.post(`/transactions/${id}/return/`);
      alert(`Book returned! Late days: ${r.data.late_days}, Fine: ₹${r.data.fine}`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || 'Return failed');
    }
  };

  return (
    <section className="panel">
      <h3>All Transactions</h3>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>Book</th>
              <th>Member</th>
              <th>Issue Date</th>
              <th>Due Date</th>
              <th>Status</th>
              <th>Fine</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {tx.map(t => (
              <tr key={t.id}>
                <td>{t.book_title}</td>
                <td>{t.member_name}</td>
                <td>{new Date(t.issue_date).toLocaleDateString()}</td>
                <td>{new Date(t.due_date).toLocaleDateString()}</td>
                <td>
                  <span className={`pill ${t.status === 'Returned' ? 'pill-returned' : ''}`}>
                    {t.status}
                  </span>
                </td>
                <td>₹{t.fine || 0}</td>
                <td>
                  {t.status === 'Issued' && (
                    <button className="small" onClick={() => ret(t.id)}>Return</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ============================================================
   ADMIN BOOK REQUESTS
   ============================================================ */
function AdminBookRequests() {
  const [requests, setRequests] = useState([]);
  const [issuingId, setIssuingId] = useState(null);
  const [filter, setFilter] = useState('all');

  const load = async () => {
    const r = await api.get('/admin/book-requests/');
    setRequests(r.data.requests);
  };

  useEffect(() => { load(); }, []);

  const issueRequest = async (requestId) => {
    setIssuingId(requestId);
    try {
      const r = await api.post(`/admin/book-requests/${requestId}/issue/`);
      alert(`${r.data.message}\nDue date: ${new Date(r.data.due_date).toLocaleDateString()}`);
      load();
    } catch (e) {
      alert(e.response?.data?.detail || 'Issue failed');
    } finally {
      setIssuingId(null);
    }
  };

  const filtered = filter === 'all' ? requests : requests.filter(r => r.status === filter);

  return (
    <section className="panel">
      <div className="toolbar">
        <h3 style={{ margin: 0 }}>Book Requests</h3>
        <div className="filter-btns">
          {['all', 'Pending', 'Issued'].map(f => (
            <button key={f} className={`small ${filter === f ? '' : 'secondary'}`} onClick={() => setFilter(f)}>
              {f === 'all' ? 'All' : f} {f === 'Pending' ? `(${requests.filter(r => r.status === 'Pending').length})` : ''}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="empty-msg">No {filter !== 'all' ? filter.toLowerCase() : ''} book requests.</p>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Book</th>
                <th>Available</th>
                <th>Requested Date</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.id}>
                  <td>
                    <b>{r.user_name}</b><br />
                    <small>{r.user_email}</small>
                  </td>
                  <td>
                    <span className={`pill ${r.role === 'teacher' ? 'pill-teacher' : 'pill-student'}`}>
                      {r.role}
                    </span>
                  </td>
                  <td>
                    <b>{r.book_title}</b>
                    {r.book_author && <><br /><small>{r.book_author}</small></>}
                  </td>
                  <td>{r.book_available}</td>
                  <td>{new Date(r.requested_at).toLocaleDateString()}</td>
                  <td>
                    <span className={`pill ${r.status === 'Pending' ? 'pill-pending' : r.status === 'Issued' ? 'pill-issued' : ''}`}>
                      {r.status}
                    </span>
                  </td>
                  <td>
                    {r.status === 'Pending' && (
                      <button
                        className="small"
                        disabled={issuingId === r.id || r.book_available < 1}
                        onClick={() => issueRequest(r.id)}
                      >
                        <CheckCircle size={14} />
                        {issuingId === r.id ? 'Issuing...' : 'Issue'}
                      </button>
                    )}
                    {r.status === 'Issued' && (
                      <span className="pill pill-issued"><CheckCircle size={12} /> Issued</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ============================================================
   ADMIN SETTINGS
   ============================================================ */
function AdminSettings() {
  const [settings, setSettings] = useState({ loan_period_days: 14, fine_per_day: 5, maximum_fine: 500 });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    api.get('/settings/').then(r => setSettings(r.data)).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    setMsg('');
    try {
      const r = await api.put('/settings/', settings);
      setMsg('Settings saved successfully!');
      setSettings({
        loan_period_days: r.data.loan_period_days,
        fine_per_day: r.data.fine_per_day,
        maximum_fine: r.data.maximum_fine,
      });
    } catch (e) {
      setMsg(e.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="settings-page">
      <section className="panel settings-panel">
        <h3><Clock size={18} /> Loan / Due Date Settings</h3>
        <p className="settings-desc">Configure the default loan period for issuing books.</p>
        <div className="settings-field">
          <label>Default Loan Period (Days)</label>
          <div className="loan-options">
            {[7, 14, 30].map(d => (
              <button key={d}
                className={`loan-btn ${settings.loan_period_days === d ? 'loan-active' : 'secondary'}`}
                onClick={() => setSettings({ ...settings, loan_period_days: d })}
              >
                {d} Days
              </button>
            ))}
            <input type="number" min="1" className="loan-custom"
              placeholder="Custom"
              value={![7, 14, 30].includes(settings.loan_period_days) ? settings.loan_period_days : ''}
              onChange={e => {
                const v = parseInt(e.target.value);
                if (v > 0) setSettings({ ...settings, loan_period_days: v });
              }}
            />
          </div>
          <small>Currently: <strong>{settings.loan_period_days} days</strong></small>
        </div>
      </section>

      <section className="panel settings-panel">
        <h3><IndianRupee size={18} /> Fine Settings</h3>
        <p className="settings-desc">Configure fine amounts for late book returns.</p>
        <div className="settings-field">
          <label>Fine Per Day (₹)</label>
          <input type="number" min="0" value={settings.fine_per_day}
            onChange={e => setSettings({ ...settings, fine_per_day: parseInt(e.target.value) || 0 })}
          />
        </div>
        <div className="settings-field">
          <label>Maximum Fine (₹)</label>
          <input type="number" min="0" value={settings.maximum_fine}
            onChange={e => setSettings({ ...settings, maximum_fine: parseInt(e.target.value) || 0 })}
          />
        </div>
        <div className="settings-example">
          <strong>Example Calculation:</strong><br />
          Book returned 3 days late → Fine = min(3 × ₹{settings.fine_per_day}, ₹{settings.maximum_fine}) = <strong>₹{Math.min(3 * settings.fine_per_day, settings.maximum_fine)}</strong>
        </div>
      </section>

      {msg && <div className={msg.includes('success') ? 'success-banner' : 'error'}>{msg}</div>}

      <button className="save-settings-btn" onClick={save} disabled={saving}>
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}

/* ============================================================
   MOUNT
   ============================================================ */
createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);
