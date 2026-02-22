import { useState, useRef, useEffect } from 'react';
import { askAI } from '../services/api';
import { Bot, Send, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer,
} from 'recharts';

const COLORS = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899'];

function MiniChart({ type, data }) {
    if (!data) return null;

    if (type === 'pie') {
        const items = Object.entries(data).map(([k, v]) => ({ name: k, value: v }));
        return (
            <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                    <Pie data={items} cx="50%" cy="50%" outerRadius={70} dataKey="value">
                        {items.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', fontSize: 12 }} />
                </PieChart>
            </ResponsiveContainer>
        );
    }

    if (type === 'bar') {
        const items = Array.isArray(data) ? data : Object.entries(data).map(([k, v]) => ({ name: k, value: v }));
        return (
            <ResponsiveContainer width="100%" height={180}>
                <BarChart data={items}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey={items[0]?.name !== undefined ? 'name' : 'priority'} tick={{ fill: '#94a3b8', fontSize: 10 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', fontSize: 12 }} />
                    <Bar dataKey={items[0]?.value !== undefined ? 'value' : items[0]?.load !== undefined ? 'load' : 'count'} fill="#3b82f6" radius={[3, 3, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
        );
    }

    if (type === 'grouped_bar') {
        // Convert nested object to flat array
        const cities = Object.keys(data);
        const types = [...new Set(cities.flatMap(c => Object.keys(data[c])))];
        const items = cities.map(city => {
            const row = { city };
            types.forEach(t => { row[t] = data[city][t] || 0; });
            return row;
        });
        return (
            <ResponsiveContainer width="100%" height={200}>
                <BarChart data={items}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="city" tick={{ fill: '#94a3b8', fontSize: 9 }} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 10 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', fontSize: 11 }} />
                    {types.map((t, i) => <Bar key={t} dataKey={t} fill={COLORS[i % COLORS.length]} stackId="a" />)}
                </BarChart>
            </ResponsiveContainer>
        );
    }

    return null;
}

export default function AIAssistant() {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([
        { role: 'bot', text: 'Привет! Я AI-ассистент. Спросите что-нибудь о распределении, например:\n• «Покажи типы обращений по городам»\n• «Нагрузка менеджеров»\n• «Тональность обращений»' },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEnd = useRef(null);

    useEffect(() => {
        messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || loading) return;

        const q = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', text: q }]);
        setLoading(true);

        try {
            const res = await askAI(q);
            const d = res.data;
            setMessages(prev => [...prev, {
                role: 'bot',
                text: d.answer,
                chart_type: d.chart_type,
                chart_data: d.data,
            }]);
        } catch {
            setMessages(prev => [...prev, { role: 'bot', text: 'Ошибка при обработке запроса. Попробуйте ещё раз.' }]);
        }
        setLoading(false);
    };

    return (
        <div className="ai-assistant">
            <AnimatePresence>
                {open && (
                    <motion.div
                        className="ai-panel"
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    >
                        <div className="ai-panel-header">
                            <h4><Bot size={18} /> AI Ассистент</h4>
                            <button className="close-btn" onClick={() => setOpen(false)} style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
                                <X size={18} />
                            </button>
                        </div>
                        <div className="ai-messages">
                            {messages.map((m, i) => (
                                <div key={i} className={`ai-msg ${m.role}`}>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{m.text}</div>
                                    {m.chart_type && m.chart_data && (
                                        <div style={{ marginTop: 12 }}>
                                            <MiniChart type={m.chart_type} data={m.chart_data} />
                                        </div>
                                    )}
                                </div>
                            ))}
                            {loading && <div className="ai-msg bot" style={{ opacity: 0.6 }}>Думаю…</div>}
                            <div ref={messagesEnd} />
                        </div>
                        <form className="ai-input-bar" onSubmit={handleSubmit}>
                            <input
                                placeholder="Задайте вопрос…"
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                disabled={loading}
                            />
                            <button type="submit" disabled={loading}><Send size={16} /></button>
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            <motion.button
                className="ai-toggle"
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setOpen(o => !o)}
            >
                <Bot size={24} color="white" />
            </motion.button>
        </div>
    );
}
