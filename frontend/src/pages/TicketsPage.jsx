import { useState, useEffect } from 'react';
import { getTickets, getTicket, deleteTicket, deleteAllTickets } from '../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, ChevronLeft, ChevronRight, Trash2, AlertTriangle } from 'lucide-react';

const TYPE_BADGES = {
    'Жалоба': 'badge-red',
    'Смена данных': 'badge-blue',
    'Консультация': 'badge-cyan',
    'Претензия': 'badge-orange',
    'Неработоспособность приложения': 'badge-purple',
    'Мошеннические действия': 'badge-pink',
    'Спам': 'badge-gray',
};

const TONALITY_BADGES = {
    'Позитивный': 'badge-green',
    'Нейтральный': 'badge-blue',
    'Негативный': 'badge-red',
};

export default function TicketsPage() {
    const [tickets, setTickets] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pages, setPages] = useState(1);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [confirmDialog, setConfirmDialog] = useState(null);

    // Filters
    const [search, setSearch] = useState('');
    const [status, setStatus] = useState('');
    const [segment, setSegment] = useState('');
    const [ticketType, setTicketType] = useState('');

    const fetchTickets = () => {
        setLoading(true);
        const params = { page, per_page: 20 };
        if (search) params.search = search;
        if (status) params.status = status;
        if (segment) params.segment = segment;
        if (ticketType) params.ticket_type = ticketType;

        getTickets(params)
            .then(r => {
                setTickets(r.data.items || []);
                setTotal(r.data.total || 0);
                setPages(r.data.pages || 1);
            })
            .catch(() => setTickets([]))
            .finally(() => setLoading(false));
    };

    useEffect(() => { fetchTickets(); }, [page, status, segment, ticketType]);

    const handleSearch = (e) => {
        e.preventDefault();
        setPage(1);
        fetchTickets();
    };

    const openDetail = async (id) => {
        setDetailLoading(true);
        try {
            const r = await getTicket(id);
            setSelected(r.data);
        } catch {
            setSelected(null);
        }
        setDetailLoading(false);
    };

    const handleDelete = (e, id) => {
        e.stopPropagation();
        setConfirmDialog({
            title: 'Удалить обращение?',
            message: 'Вы уверены, что хотите удалить это обращение? Это действие нельзя отменить.',
            isDestructive: true,
            onConfirm: async () => {
                setConfirmDialog(null);
                try {
                    await deleteTicket(id);
                    fetchTickets();
                } catch (err) {
                    console.error('Failed to delete ticket', err);
                    alert('Ошибка при удалении обращения');
                }
            }
        });
    };

    const handleDeleteAll = () => {
        setConfirmDialog({
            title: 'Удалить ВСЕ обращения?',
            message: 'ВНИМАНИЕ! Вы собираетесь удалить ВСЕ обращения из базы. Это действие абсолютно необратимо.',
            isDestructive: true,
            confirmText: 'Да, удалить всё',
            onConfirm: async () => {
                setConfirmDialog(null);
                try {
                    await deleteAllTickets();
                    fetchTickets();
                } catch (err) {
                    console.error('Failed to delete all tickets', err);
                    alert('Ошибка при удалении всех обращений');
                }
            }
        });
    };

    const getPriorityClass = (p) => {
        if (p >= 7) return 'priority-high';
        if (p >= 4) return 'priority-medium';
        return 'priority-low';
    };

    return (
        <>
            <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2>Обращения</h2>
                    <p>Всего: {total} обращений</p>
                </div>
                {total > 0 && (
                    <button className="btn" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)' }} onClick={handleDeleteAll}>
                        <Trash2 size={16} /> Удалить все
                    </button>
                )}
            </div>

            {/* Filters */}
            <form onSubmit={handleSearch} className="filters-bar">
                <div style={{ position: 'relative' }}>
                    <input
                        placeholder="Поиск по тексту обращения…"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
                <select value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
                    <option value="">Все статусы</option>
                    <option value="new">Новые</option>
                    <option value="analyzed">Проанализированы</option>
                    <option value="distributed">Распределены</option>
                </select>
                <select value={segment} onChange={e => { setSegment(e.target.value); setPage(1); }}>
                    <option value="">Все сегменты</option>
                    <option value="Mass">Mass</option>
                    <option value="VIP">VIP</option>
                    <option value="Priority">Priority</option>
                </select>
                <select value={ticketType} onChange={e => { setTicketType(e.target.value); setPage(1); }}>
                    <option value="">Все типы</option>
                    <option value="Жалоба">Жалоба</option>
                    <option value="Смена данных">Смена данных</option>
                    <option value="Консультация">Консультация</option>
                    <option value="Претензия">Претензия</option>
                    <option value="Неработоспособность приложения">Неработоспособность</option>
                    <option value="Мошеннические действия">Мошенничество</option>
                    <option value="Спам">Спам</option>
                </select>
                <button type="submit" className="btn btn-secondary"><Search size={16} /> Найти</button>
            </form>

            {/* Table */}
            {loading ? (
                <div className="spinner" />
            ) : (
                <div className="table-container" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, overflow: 'hidden' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>GUID клиента</th>
                                <th>Сегмент</th>
                                <th>Город</th>
                                <th>Тип</th>
                                <th>Тональность</th>
                                <th>Приоритет</th>
                                <th>Менеджер</th>
                                <th>Статус</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {tickets.map(t => (
                                <tr key={t.id} style={{ cursor: 'pointer' }} onClick={() => openDetail(t.id)}>
                                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{t.client_guid?.slice(0, 12)}…</td>
                                    <td><span className={`badge ${t.segment === 'VIP' ? 'badge-orange' : t.segment === 'Priority' ? 'badge-purple' : 'badge-gray'}`}>{t.segment}</span></td>
                                    <td>{t.city || '—'}</td>
                                    <td>{t.ai_analysis ? <span className={`badge ${TYPE_BADGES[t.ai_analysis.type] || 'badge-gray'}`}>{t.ai_analysis.type}</span> : '—'}</td>
                                    <td>{t.ai_analysis ? <span className={`badge ${TONALITY_BADGES[t.ai_analysis.tonality] || 'badge-gray'}`}>{t.ai_analysis.tonality}</span> : '—'}</td>
                                    <td>{t.ai_analysis ? <span className={getPriorityClass(t.ai_analysis.priority)}><strong>{t.ai_analysis.priority}</strong></span> : '—'}</td>
                                    <td>{t.assigned_manager ? t.assigned_manager.full_name : '—'}</td>
                                    <td><span className={`badge ${t.status === 'distributed' ? 'badge-green' : t.status === 'analyzed' ? 'badge-blue' : 'badge-gray'}`}>{t.status}</span></td>
                                    <td>
                                        <button
                                            className="icon-btn"
                                            onClick={(e) => handleDelete(e, t.id)}
                                            style={{ color: 'var(--text-muted)' }}
                                            title="Удалить"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {tickets.length === 0 && (
                                <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>Нет обращений</td></tr>
                            )}
                        </tbody>
                    </table>

                    {/* Pagination */}
                    {pages > 1 && (
                        <div className="pagination">
                            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={14} /></button>
                            {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
                                const p = i + 1;
                                return <button key={p} className={p === page ? 'active' : ''} onClick={() => setPage(p)}>{p}</button>;
                            })}
                            {pages > 7 && <span style={{ color: 'var(--text-muted)' }}>…</span>}
                            <button disabled={page >= pages} onClick={() => setPage(p => p + 1)}><ChevronRight size={14} /></button>
                        </div>
                    )}
                </div>
            )}

            {/* Detail Modal */}
            <AnimatePresence>
                {selected && (
                    <motion.div
                        className="modal-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setSelected(null)}
                    >
                        <motion.div
                            className="modal-content"
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            onClick={e => e.stopPropagation()}
                        >
                            <h3>
                                Обращение
                                <button className="close-btn" onClick={() => setSelected(null)}><X /></button>
                            </h3>

                            <div className="modal-section">
                                <h4>Клиент</h4>
                                <div className="detail-grid">
                                    <div className="detail-item"><div className="label">GUID</div><div className="value" style={{ fontFamily: 'monospace', fontSize: 12 }}>{selected.client_guid}</div></div>
                                    <div className="detail-item"><div className="label">Сегмент</div><div className="value">{selected.segment}</div></div>
                                    <div className="detail-item"><div className="label">Пол</div><div className="value">{selected.gender || '—'}</div></div>
                                    <div className="detail-item"><div className="label">Дата рождения</div><div className="value">{selected.birth_date || '—'}</div></div>
                                </div>
                            </div>

                            <div className="modal-section">
                                <h4>Адрес</h4>
                                <div className="detail-grid">
                                    <div className="detail-item"><div className="label">Страна</div><div className="value">{selected.country || '—'}</div></div>
                                    <div className="detail-item"><div className="label">Область</div><div className="value">{selected.region || '—'}</div></div>
                                    <div className="detail-item"><div className="label">Город</div><div className="value">{selected.city || '—'}</div></div>
                                    <div className="detail-item"><div className="label">Улица, дом</div><div className="value">{`${selected.street || ''} ${selected.house || ''}`.trim() || '—'}</div></div>
                                </div>
                            </div>

                            <div className="modal-section">
                                <h4>Описание</h4>
                                <p style={{ fontSize: 14, lineHeight: 1.7, color: 'var(--text-secondary)' }}>{selected.description || '—'}</p>
                            </div>

                            {selected.ai_analysis && (
                                <div className="modal-section">
                                    <h4>AI-анализ</h4>
                                    <div className="detail-grid">
                                        <div className="detail-item"><div className="label">Тип</div><div className="value"><span className={`badge ${TYPE_BADGES[selected.ai_analysis.type] || 'badge-gray'}`}>{selected.ai_analysis.type}</span></div></div>
                                        <div className="detail-item"><div className="label">Тональность</div><div className="value"><span className={`badge ${TONALITY_BADGES[selected.ai_analysis.tonality] || 'badge-gray'}`}>{selected.ai_analysis.tonality}</span></div></div>
                                        <div className="detail-item"><div className="label">Приоритет</div><div className="value"><span className={getPriorityClass(selected.ai_analysis.priority)}><strong>{selected.ai_analysis.priority}/10</strong></span></div></div>
                                        <div className="detail-item"><div className="label">Язык</div><div className="value">{selected.ai_analysis.language}</div></div>
                                    </div>
                                    <p style={{ fontSize: 13, marginTop: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}><strong>Summary:</strong> {selected.ai_analysis.summary}</p>
                                </div>
                            )}

                            {selected.distribution && (
                                <div className="modal-section">
                                    <h4>Назначение</h4>
                                    <div className="detail-grid">
                                        <div className="detail-item"><div className="label">Менеджер</div><div className="value">{selected.distribution.manager?.full_name || '—'}</div></div>
                                        <div className="detail-item"><div className="label">Должность</div><div className="value">{selected.distribution.manager?.position || '—'}</div></div>
                                        <div className="detail-item"><div className="label">Дата назначения</div><div className="value">{selected.distribution.assigned_at ? new Date(selected.distribution.assigned_at).toLocaleString('ru-RU') : '—'}</div></div>
                                    </div>
                                    <p style={{ fontSize: 13, marginTop: 8, color: 'var(--text-muted)' }}>{selected.distribution.reason}</p>
                                </div>
                            )}
                        </motion.div>
                    </motion.div>
                )}

                {/* Confirm Dialog Modal */}
                {confirmDialog && (
                    <motion.div
                        className="modal-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setConfirmDialog(null)}
                        style={{ zIndex: 1000 }}
                    >
                        <motion.div
                            className="modal-content"
                            initial={{ scale: 0.95, opacity: 0, y: 20 }}
                            animate={{ scale: 1, opacity: 1, y: 0 }}
                            exit={{ scale: 0.95, opacity: 0, y: 20 }}
                            onClick={e => e.stopPropagation()}
                            style={{ maxWidth: 400, textAlign: 'center', padding: '32px 24px' }}
                        >
                            <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 64, height: 64, borderRadius: '50%', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', marginBottom: 24 }}>
                                <AlertTriangle size={32} />
                            </div>
                            <h3 style={{ color: '#f1f5f9', fontSize: 20, marginBottom: 12, borderBottom: 'none', padding: 0 }}>
                                {confirmDialog.title}
                            </h3>
                            <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6, marginBottom: 32 }}>
                                {confirmDialog.message}
                            </p>
                            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
                                <button
                                    className="btn"
                                    style={{ background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)', flex: 1 }}
                                    onClick={() => setConfirmDialog(null)}
                                >
                                    Отмена
                                </button>
                                <button
                                    className="btn"
                                    style={{
                                        background: confirmDialog.isDestructive ? '#ef4444' : 'var(--accent-primary)',
                                        color: '#fff',
                                        border: 'none',
                                        flex: 1
                                    }}
                                    onClick={confirmDialog.onConfirm}
                                >
                                    {confirmDialog.confirmText || 'Удалить'}
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
