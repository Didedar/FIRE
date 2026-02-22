import { getManagers, getOffices, deleteManager, deleteAllManagers, deleteOffice, deleteAllOffices } from '../services/api';
import { Trash2, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import { useState, useEffect } from 'react';

export default function ManagersPage() {
    const [managers, setManagers] = useState([]);
    const [offices, setOffices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [confirmDialog, setConfirmDialog] = useState(null);

    const fetchData = () => {
        setLoading(true);
        Promise.all([getManagers(), getOffices()])
            .then(([mRes, oRes]) => {
                setManagers(mRes.data.items || []);
                setOffices(oRes.data.items || []);
            })
            .catch(() => { })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleDeleteManager = (id) => {
        setConfirmDialog({
            title: 'Удалить менеджера?',
            message: 'Вы действительно хотите удалить этого менеджера? Это действие необратимо.',
            isDestructive: true,
            onConfirm: async () => {
                setConfirmDialog(null);
                try { await deleteManager(id); fetchData(); } catch (e) { alert('Ошибка'); }
            }
        });
    };

    const handleDeleteAllManagers = () => {
        setConfirmDialog({
            title: 'Удалить всех менеджеров?',
            message: 'ВНИМАНИЕ! Вы собираетесь удалить ВСЕХ менеджеров. Продолжить?',
            isDestructive: true,
            confirmText: 'Да, удалить всех',
            onConfirm: async () => {
                setConfirmDialog(null);
                try { await deleteAllManagers(); fetchData(); } catch (e) { alert('Ошибка'); }
            }
        });
    };

    const handleDeleteOffice = (id) => {
        setConfirmDialog({
            title: 'Удалить офис?',
            message: 'Удалить этот офис? У всех менеджеров в этом офисе сбросится привязка.',
            isDestructive: true,
            onConfirm: async () => {
                setConfirmDialog(null);
                try { await deleteOffice(id); fetchData(); } catch (e) { alert('Ошибка'); }
            }
        });
    };

    const handleDeleteAllOffices = () => {
        setConfirmDialog({
            title: 'Удалить ВСЕ офисы?',
            message: 'ВНИМАНИЕ! У всех менеджеров сбросится территориальная привязка. Продолжить?',
            isDestructive: true,
            confirmText: 'Да, удалить все',
            onConfirm: async () => {
                setConfirmDialog(null);
                try { await deleteAllOffices(); fetchData(); } catch (e) { alert('Ошибка'); }
            }
        });
    };

    if (loading) return <div className="spinner" />;

    const chartData = managers
        .sort((a, b) => b.current_load - a.current_load)
        .slice(0, 15)
        .map(m => ({ name: m.full_name.split(' ').slice(0, 2).join(' '), load: m.current_load }));

    return (
        <>
            <div className="page-header">
                <h2>Менеджеры</h2>
                <p>Всего менеджеров: {managers.length} | Офисов: {offices.length}</p>
            </div>

            {/* Load Chart */}
            {chartData.length > 0 && (
                <div className="chart-card" style={{ marginBottom: 40, background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, padding: 32 }}>
                    <h3 style={{ color: 'var(--text-primary)', fontSize: 18, marginBottom: 32 }}>Нагрузка менеджеров (Топ-15)</h3>
                    <ResponsiveContainer width="100%" height={320}>
                        <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                            <XAxis dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} angle={-30} textAnchor="end" height={80} stroke="rgba(255,255,255,0.1)" />
                            <YAxis stroke="rgba(255,255,255,0.1)" tick={{ fill: 'var(--text-secondary)' }} />
                            <Tooltip cursor={{ fill: 'rgba(255,255,255,0.02)' }} contentStyle={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 8, color: '#f1f5f9' }} />
                            <Bar dataKey="load" fill="var(--accent-primary)" radius={[4, 4, 0, 0]} barSize={30} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}

            {/* Managers Table */}
            <div className="table-container" style={{ marginBottom: 28 }}>
                <div className="table-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3>Менеджеры</h3>
                    {managers.length > 0 && (
                        <button className="btn" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '6px 12px' }} onClick={handleDeleteAllManagers}>
                            <Trash2 size={16} /> Удалить всех менеджеров
                        </button>
                    )}
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>ФИО</th>
                            <th>Должность</th>
                            <th>Навыки</th>
                            <th>Офис</th>
                            <th>Нагрузка</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {managers.map(m => (
                            <tr key={m.id}>
                                <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{m.full_name}</td>
                                <td>
                                    <span className={`badge ${m.position.includes('Глав') ? 'badge-purple' : m.position.includes('Ведущий') ? 'badge-blue' : 'badge-gray'}`}>
                                        {m.position}
                                    </span>
                                </td>
                                <td>
                                    {(m.skills || []).map(s => (
                                        <span key={s} className={`badge ${s === 'VIP' ? 'badge-orange' : s === 'ENG' ? 'badge-cyan' : s === 'KZ' ? 'badge-green' : 'badge-gray'}`} style={{ marginRight: 4 }}>
                                            {s}
                                        </span>
                                    ))}
                                    {(!m.skills || m.skills.length === 0) && '—'}
                                </td>
                                <td>{m.business_unit_name || '—'}</td>
                                <td>
                                    <span style={{
                                        fontWeight: 600,
                                        color: m.current_load > 20 ? 'var(--accent-red)' : m.current_load > 10 ? 'var(--accent-orange)' : 'var(--accent-green)',
                                    }}>
                                        {m.current_load}
                                    </span>
                                </td>
                                <td>
                                    <button
                                        className="icon-btn"
                                        onClick={() => handleDeleteManager(m.id)}
                                        style={{ color: 'var(--text-muted)' }}
                                        title="Удалить"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Offices Table */}
            <div className="table-container">
                <div className="table-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3>Офисы (Бизнес-единицы)</h3>
                    {offices.length > 0 && (
                        <button className="btn" style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '6px 12px' }} onClick={handleDeleteAllOffices}>
                            <Trash2 size={16} /> Удалить все офисы
                        </button>
                    )}
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Офис</th>
                            <th>Адрес</th>
                            <th>Координаты</th>
                            <th></th>
                        </tr>
                    </thead>
                    <tbody>
                        {offices.map(o => (
                            <tr key={o.id}>
                                <td style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{o.name}</td>
                                <td>{o.address || '—'}</td>
                                <td style={{ fontFamily: 'monospace', fontSize: 12 }}>
                                    {o.latitude && o.longitude ? `${o.latitude.toFixed(4)}, ${o.longitude.toFixed(4)}` : '—'}
                                </td>
                                <td>
                                    <button
                                        className="icon-btn"
                                        onClick={() => handleDeleteOffice(o.id)}
                                        style={{ color: 'var(--text-muted)' }}
                                        title="Удалить"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Confirm Dialog Modal */}
            <AnimatePresence>
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
