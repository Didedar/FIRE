import { useState, useEffect } from 'react';
import { getStats } from '../services/api';
import {
    BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Legend, LineChart, Line
} from 'recharts';

// Neon & Dark theme charts colors
const COLORS = ['#ccff00', '#ffffff', '#64748b', '#3b82f6', '#8b5cf6', '#06b6d4', '#ec4899'];
const TONALITY_COLORS = { 'Позитивный': '#ccff00', 'Нейтральный': '#ffffff', 'Негативный': '#ef4444' };

export default function Dashboard() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        getStats()
            .then(r => setStats(r.data))
            .catch(() => setStats(null))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="spinner" />;

    if (!stats) {
        return (
            <div className="page-header" style={{ textAlign: 'center', marginTop: 100 }}>
                <h2 style={{ fontSize: 48, fontWeight: 700, color: 'var(--accent-primary)' }}>Дашборд</h2>
                <p style={{ fontSize: 18, color: 'var(--text-secondary)' }}>Нет данных. Загрузите файлы для запуска аналитики.</p>
            </div>
        );
    }

    const typeData = Object.entries(stats.type_distribution || {}).map(([k, v]) => ({ name: k, value: v }));
    const tonData = Object.entries(stats.tonality_distribution || {}).map(([k, v]) => ({ name: k, value: v }));
    const langData = Object.entries(stats.language_distribution || {}).map(([k, v]) => ({ name: k, value: v }));
    const loadData = (stats.manager_load || []).slice(0, 12);
    const officeData = Object.entries(stats.office_distribution || {}).map(([k, v]) => ({ name: k, value: v }));

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '64px' }}>

            {/* HERO SECTION */}
            <section className="hero-section" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '20px' }}>
                <div style={{ maxWidth: '600px' }}>
                    <div style={{ textTransform: 'uppercase', letterSpacing: '2px', color: 'var(--accent-primary)', fontSize: '13px', fontWeight: 700, marginBottom: '24px' }}>
                        Оптимизируйте ваши процессы !
                    </div>
                    <h1 style={{ fontSize: '64px', fontWeight: 800, lineHeight: 1.1, marginBottom: '32px' }}>
                        Лучшая <span style={{ color: 'var(--text-secondary)' }}>бизнес</span><br />
                        <span style={{ color: 'var(--accent-primary)' }}>аналитика обращений</span><br />
                        <span style={{ color: 'var(--text-secondary)' }}>для будущего.</span>
                    </h1>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
                        <div style={{ display: 'flex' }}>
                            {[1, 2, 3, 4].map((i) => (
                                <div key={i} style={{
                                    width: 40, height: 40, borderRadius: '50%', backgroundColor: `rgba(255,255,255,0.${i}5)`,
                                    border: '2px solid var(--bg-primary)', marginLeft: i > 1 ? -15 : 0,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12
                                }}>
                                    👤
                                </div>
                            ))}
                        </div>
                        <div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>{stats.total_tickets}K+</div>
                            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Всего обращений</div>
                        </div>
                    </div>
                </div>

                {/* Visual abstract representation (simulating the phone mockup) */}
                <div style={{ position: 'relative', width: 400, height: 400 }}>
                    <div style={{
                        position: 'absolute', right: 0, top: 0, width: 280, height: 380,
                        background: 'linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(204,255,0,0.05) 100%)',
                        border: '1px solid rgba(204,255,0,0.2)', borderRadius: 30, padding: 24,
                        boxShadow: '0 20px 40px rgba(0,0,0,0.5), inset 0 1px 1px rgba(255,255,255,0.1)',
                        transform: 'rotate(5deg)'
                    }}>
                        <div style={{ textAlign: 'center', marginBottom: 20 }}>
                            <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Средний приоритет</div>
                            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--text-primary)' }}>{stats.avg_priority} / 10</div>
                        </div>
                        <div style={{ height: 120 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={[{ v: 1 }, { v: 3 }, { v: 2 }, { v: 5 }, { v: 4 }, { v: 7 }]}>
                                    <Line type="monotone" dataKey="v" stroke="var(--accent-primary)" strokeWidth={3} dot={false} />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                        <div style={{ marginTop: 20, padding: 16, background: 'rgba(0,0,0,0.3)', borderRadius: 12 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Ожидают</span>
                                <span style={{ fontWeight: 600 }}>{stats.pending_tickets}</span>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                <span style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Анализировано</span>
                                <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>{stats.total_tickets - stats.pending_tickets}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* 3-CARD HIGHLIGHT SECTION */}
            <section>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 40 }}>
                    <h2 style={{ fontSize: '40px', fontWeight: 700, lineHeight: 1.2, maxWidth: 400 }}>
                        Ваш <span style={{ color: 'var(--accent-primary)' }}>надежный</span> партнер в анализе.
                    </h2>
                    <p style={{ color: 'var(--text-secondary)', fontSize: 14, maxWidth: 350, lineHeight: 1.6 }}>
                        Платформа помогает автоматически распределять обращения клиентов по менеджерам, используя ИИ для оценки приоритета и тональности.
                    </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
                    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, padding: 32 }}>
                        <div style={{ color: 'var(--accent-primary)', fontWeight: 700, fontSize: 20, marginBottom: 16 }}>01.</div>
                        <h3 style={{ fontSize: 24, fontWeight: 600, marginBottom: 24, lineHeight: 1.3 }}>Интеллектуальное<br />распределение.</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6 }}>
                            Система анализирует текст обращений и направляет их наиболее подходящему специалисту.
                        </p>
                    </div>
                    <div style={{ background: 'var(--gradient-primary)', borderRadius: 24, padding: 32, color: 'var(--bg-primary)', boxShadow: 'var(--shadow-glow)' }}>
                        <div style={{ fontWeight: 800, fontSize: 20, marginBottom: 16 }}>02.</div>
                        <h3 style={{ fontSize: 24, fontWeight: 800, marginBottom: 24, lineHeight: 1.3 }}>Эффективность<br />процессов.</h3>
                        <p style={{ fontSize: 14, lineHeight: 1.6, fontWeight: 500, opacity: 0.9, marginBottom: 32 }}>
                            Сэкономьте часы работы за счет автоматического назначения и оценки приоритетов заявок {stats.total_tickets > 0 ? `(${Math.round((stats.distributed_tickets / stats.total_tickets) * 100)}% автоматизировано)` : ''}.
                        </p>
                        <a href="#" style={{ color: 'var(--bg-primary)', fontWeight: 700, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 8 }}>
                            Подробнее →
                        </a>
                    </div>
                    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, padding: 32 }}>
                        <div style={{ color: 'var(--accent-primary)', fontWeight: 700, fontSize: 20, marginBottom: 16 }}>03.</div>
                        <h3 style={{ fontSize: 24, fontWeight: 600, marginBottom: 24, lineHeight: 1.3 }}>Абсолютный<br />контроль.</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.6 }}>
                            Отслеживайте нагрузку менеджеров в реальном времени и принимайте решения на основе данных.
                        </p>
                    </div>
                </div>
            </section>

            {/* Charts Section */}
            <section style={{ marginTop: 40 }}>
                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 60 }}>
                    <h2 style={{ fontSize: 28, fontWeight: 700, marginBottom: 32 }}>Аналитика платформы</h2>

                    <div className="charts-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '24px' }}>
                        {/* Type Distribution */}
                        <div className="chart-card" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, padding: 32 }}>
                            <h3 style={{ color: 'var(--text-primary)', fontSize: 18, marginBottom: 24 }}>Типы обращений</h3>
                            {typeData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={280}>
                                    <PieChart>
                                        <Pie data={typeData} cx="50%" cy="50%" innerRadius={70} outerRadius={100} dataKey="value" stroke="none" label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}>
                                            {typeData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                                        </Pie>
                                        <Tooltip contentStyle={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 8, color: '#f1f5f9' }} itemStyle={{ color: 'var(--text-primary)' }} />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Нет данных</p>}
                        </div>

                        {/* Tonality */}
                        <div className="chart-card" style={{ background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, padding: 32 }}>
                            <h3 style={{ color: 'var(--text-primary)', fontSize: 18, marginBottom: 24 }}>Тональность</h3>
                            {tonData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={280}>
                                    <PieChart>
                                        <Pie data={tonData} cx="50%" cy="50%" innerRadius={70} outerRadius={100} dataKey="value" stroke="none" label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}>
                                            {tonData.map((entry, i) => <Cell key={i} fill={TONALITY_COLORS[entry.name] || COLORS[i]} />)}
                                        </Pie>
                                        <Tooltip contentStyle={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 8, color: '#f1f5f9' }} />
                                    </PieChart>
                                </ResponsiveContainer>
                            ) : <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Нет данных</p>}
                        </div>

                        {/* Manager Load */}
                        <div className="chart-card" style={{ gridColumn: '1 / -1', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: 24, padding: 32 }}>
                            <h3 style={{ color: 'var(--text-primary)', fontSize: 18, marginBottom: 32 }}>Нагрузка менеджеров</h3>
                            {loadData.length > 0 ? (
                                <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={loadData} layout="vertical" margin={{ left: 80 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" horizontal={false} />
                                        <XAxis type="number" stroke="#64748b" />
                                        <YAxis dataKey="name" type="category" width={100} tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                                        <Tooltip cursor={{ fill: 'rgba(255,255,255,0.02)' }} contentStyle={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)', borderRadius: 8, color: '#f1f5f9' }} />
                                        <Bar dataKey="load" fill="var(--accent-primary)" radius={[0, 4, 4, 0]} barSize={20} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>Нет данных</p>}
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
}
