import { useState, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FlaskConical, Send, X, ChevronRight, User, Brain, MapPin, Search, Sparkles, Shield, Clock, Globe, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const LOADING_STEPS = [
    { icon: Brain, text: 'Анализ текста в NLP модуле...', duration: 1200 },
    { icon: MapPin, text: 'Определение гео-позиции...', duration: 1200 },
    { icon: Search, text: 'Поиск лучшего менеджера...', duration: 1200 }
];

/* ── Welcome State ─────────────────────────────────── */

function WelcomeState({ onStart }) {
    return (
        <motion.div
            className="dist-welcome"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -30, scale: 0.95 }}
            transition={{ duration: 0.5 }}
        >
            <div className="dist-welcome-glow" />
            <div className="dist-welcome-content">
                <div className="dist-welcome-badge">
                    <Sparkles size={14} />
                    <span>Playground</span>
                </div>
                <h1 className="dist-welcome-title">
                    Тестирование алгоритма<br />
                    <span className="dist-accent">F.I.R.E.</span>
                </h1>
                <p className="dist-welcome-desc">
                    Введите текст обращения клиента и наблюдайте, как система анализирует его
                    в реальном времени — определяет тип, тональность, приоритет и назначает
                    лучшего менеджера.
                </p>
                <button className="btn btn-primary dist-start-btn" onClick={onStart}>
                    <FlaskConical size={18} />
                    Показать функционал
                    <ChevronRight size={16} />
                </button>
            </div>

            {/* Decorative elements */}
            <div className="dist-welcome-visual">
                <div className="dist-orbit dist-orbit-1" />
                <div className="dist-orbit dist-orbit-2" />
                <div className="dist-orbit dist-orbit-3" />
                <div className="dist-orbit-center">
                    <FlaskConical size={32} />
                </div>
            </div>
        </motion.div>
    );
}

/* ── Ticket Input Form ─────────────────────────────── */

function TicketInputForm({ ticketText, setTicketText, onSubmit, isLoading }) {
    const placeholder = `Например: "Здравствуйте! Я сделал заказ 2 недели назад, номер заказа #4521. Товар до сих пор не доставлен, хотя обещали за 3-5 дней. Прошу разобраться и ускорить доставку или вернуть деньги. Город — Алматы."`;

    return (
        <motion.div
            className="dist-input-panel"
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
        >
            <div className="dist-panel-header">
                <div className="dist-panel-icon">
                    <Send size={18} />
                </div>
                <div>
                    <h3>Новое обращение</h3>
                    <p>Введите текст жалобы или запроса клиента</p>
                </div>
            </div>

            <div className="dist-form-body">
                <textarea
                    className="dist-textarea"
                    value={ticketText}
                    onChange={(e) => setTicketText(e.target.value)}
                    placeholder={placeholder}
                    disabled={isLoading}
                    rows={8}
                />

                <div className="dist-form-footer">
                    <div className="dist-char-count">
                        {ticketText.length} символов
                    </div>
                    <button
                        className="btn btn-primary"
                        onClick={onSubmit}
                        disabled={isLoading || ticketText.trim().length < 10}
                    >
                        {isLoading ? (
                            <>
                                <div className="dist-btn-spinner" />
                                Обработка...
                            </>
                        ) : (
                            <>
                                <Send size={16} />
                                Запустить распределение
                            </>
                        )}
                    </button>
                </div>
            </div>
        </motion.div>
    );
}

/* ── Processing Loader ─────────────────────────────── */

function ProcessingLoader({ currentStep }) {
    return (
        <motion.div
            className="dist-loader"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
        >
            <div className="dist-loader-header">
                <div className="dist-loader-pulse" />
                <span>Обработка запроса</span>
            </div>
            <div className="dist-steps">
                {LOADING_STEPS.map((step, idx) => {
                    const StepIcon = step.icon;
                    const status = idx < currentStep ? 'done' : idx === currentStep ? 'active' : 'pending';
                    return (
                        <motion.div
                            key={idx}
                            className={`dist-step dist-step-${status}`}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: idx * 0.15 }}
                        >
                            <div className="dist-step-indicator">
                                {status === 'done' ? (
                                    <motion.div
                                        className="dist-step-check"
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        transition={{ type: 'spring', stiffness: 300 }}
                                    >✓</motion.div>
                                ) : status === 'active' ? (
                                    <div className="dist-step-spinner" />
                                ) : (
                                    <div className="dist-step-dot" />
                                )}
                            </div>
                            <StepIcon size={18} className="dist-step-icon" />
                            <span className="dist-step-text">{step.text}</span>
                        </motion.div>
                    );
                })}
            </div>
        </motion.div>
    );
}

/* ── Error Banner ──────────────────────────────────── */

function ErrorBanner({ message, onDismiss }) {
    return (
        <motion.div
            className="dist-error-banner"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
        >
            <AlertTriangle size={18} />
            <span>{message}</span>
            <button className="dist-error-close" onClick={onDismiss}>
                <X size={16} />
            </button>
        </motion.div>
    );
}

/* ── Manager Result Card ───────────────────────────── */

function ManagerResultCard({ manager, nlpSummary, index, onClick }) {
    const loadPercent = manager.max_load > 0
        ? Math.round((manager.current_load / manager.max_load) * 100)
        : 0;

    return (
        <motion.div
            className="dist-manager-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: index * 0.15 }}
            onClick={onClick}
            whileHover={{ y: -2, transition: { duration: 0.2 } }}
        >
            <div className="dist-card-rank">#{index + 1}</div>

            <div className="dist-card-header">
                <div className="dist-avatar">
                    <User size={20} />
                </div>
                <div className="dist-card-info">
                    <h4>{manager.name}</h4>
                    <span className="dist-card-office">
                        <MapPin size={12} />
                        {manager.office || '—'}
                    </span>
                </div>
                {manager.position && (
                    <div className="dist-match-score">
                        <div className="dist-match-value" style={{ fontSize: 14 }}>{manager.position}</div>
                    </div>
                )}
            </div>

            <div className="dist-card-badges">
                <span className="badge badge-blue">{nlpSummary.detected_type}</span>
                <span className={`badge ${nlpSummary.tonality === 'Негативный' ? 'badge-red' : nlpSummary.tonality === 'Позитивный' ? 'badge-green' : 'badge-gray'}`}>
                    {nlpSummary.tonality}
                </span>
                <span className={`badge ${nlpSummary.priority >= 7 ? 'badge-red' : nlpSummary.priority >= 4 ? 'badge-orange' : 'badge-green'}`}>
                    Приоритет: {nlpSummary.priority}/10
                </span>
            </div>

            <div className="dist-card-load">
                <div className="dist-load-header">
                    <span>Нагрузка</span>
                    <span>{manager.current_load}/{manager.max_load}</span>
                </div>
                <div className="dist-load-bar">
                    <motion.div
                        className="dist-load-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${loadPercent}%` }}
                        transition={{ duration: 0.8, delay: 0.3 + index * 0.15 }}
                        style={{
                            background: loadPercent > 80 ? 'var(--accent-red)' : loadPercent > 50 ? 'var(--accent-orange)' : 'var(--accent-primary)'
                        }}
                    />
                </div>
            </div>

            {manager.skills && manager.skills.length > 0 && (
                <div className="dist-card-skills">
                    {manager.skills.map((skill, i) => (
                        <span key={i} className="dist-skill-tag">{skill}</span>
                    ))}
                </div>
            )}

            <div className="dist-card-action">
                <span>Подробнее</span>
                <ChevronRight size={14} />
            </div>
        </motion.div>
    );
}

/* ── Detail Modal ──────────────────────────────────── */

function DetailModal({ manager, nlpSummary, rawApiResponse, onClose }) {
    const fullData = useMemo(() => ({
        api_response: rawApiResponse,
        nlp_analysis: {
            summary: nlpSummary.summary,
            language: nlpSummary.language,
            detected_type: nlpSummary.detected_type,
            tonality: nlpSummary.tonality,
            priority: nlpSummary.priority,
            geo_data: nlpSummary.geo_data
        },
        assigned_manager: {
            id: manager.id,
            name: manager.name,
            office: manager.office,
            position: manager.position,
            skills: manager.skills,
            current_load: manager.current_load,
            max_load: manager.max_load,
        },
        assignment_reason: manager.assignment_reason
    }), [manager, nlpSummary, rawApiResponse]);

    return (
        <motion.div
            className="dist-modal-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
        >
            <motion.div
                className="dist-modal"
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="dist-modal-header">
                    <div className="dist-modal-title">
                        <Shield size={20} />
                        <h3>Детали назначения</h3>
                    </div>
                    <button className="dist-modal-close" onClick={onClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="dist-modal-body">
                    {/* Manager Info */}
                    <div className="dist-modal-section">
                        <h4><User size={16} /> Менеджер</h4>
                        <div className="dist-modal-manager">
                            <div className="dist-avatar dist-avatar-lg">
                                <User size={28} />
                            </div>
                            <div>
                                <div className="dist-modal-name">{manager.name}</div>
                                <div className="dist-modal-office">
                                    <MapPin size={13} /> {manager.office || '—'}
                                </div>
                                {manager.position && (
                                    <div className="dist-modal-contact">{manager.position}</div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* NLP Summary */}
                    <div className="dist-modal-section">
                        <h4><Brain size={16} /> NLP Анализ</h4>
                        <div className="dist-modal-grid">
                            <div className="dist-modal-item">
                                <span className="dist-modal-label"><Globe size={13} /> Язык</span>
                                <span className="dist-modal-value">{nlpSummary.language?.toUpperCase()}</span>
                            </div>
                            <div className="dist-modal-item">
                                <span className="dist-modal-label">Тип</span>
                                <span className="dist-modal-value">{nlpSummary.detected_type}</span>
                            </div>
                            <div className="dist-modal-item">
                                <span className="dist-modal-label">Тональность</span>
                                <span className="dist-modal-value">{nlpSummary.tonality}</span>
                            </div>
                            <div className="dist-modal-item">
                                <span className="dist-modal-label"><Clock size={13} /> Приоритет</span>
                                <span className="dist-modal-value">{nlpSummary.priority}/10</span>
                            </div>
                        </div>
                        {nlpSummary.summary && (
                            <div className="dist-modal-summary">
                                <p>{nlpSummary.summary}</p>
                            </div>
                        )}
                    </div>

                    {/* Assignment Reason */}
                    <div className="dist-modal-section">
                        <h4><Sparkles size={16} /> Причина назначения</h4>
                        <p className="dist-modal-reason">{manager.assignment_reason}</p>
                    </div>

                    {/* Processing Time */}
                    {rawApiResponse?.processing_time_ms && (
                        <div className="dist-modal-section">
                            <h4><Clock size={16} /> Время обработки</h4>
                            <p className="dist-modal-reason">
                                {rawApiResponse.processing_time_ms.toFixed(0)} мс
                            </p>
                        </div>
                    )}

                    {/* Full JSON */}
                    <div className="dist-modal-section">
                        <h4>📋 Полный JSON-ответ API</h4>
                        <pre className="dist-json-block">
                            <code>{JSON.stringify(fullData, null, 2)}</code>
                        </pre>
                    </div>
                </div>
            </motion.div>
        </motion.div>
    );
}

/* ── Results Area ──────────────────────────────────── */

function ResultsArea({ resultData, onSelectManager }) {
    if (!resultData) return null;

    return (
        <motion.div
            className="dist-results-panel"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
        >
            <div className="dist-panel-header">
                <div className="dist-panel-icon dist-panel-icon-green">
                    <Sparkles size={18} />
                </div>
                <div>
                    <h3>Результаты распределения</h3>
                    <p>
                        Статус: {resultData.status}
                        {resultData.processing_time_ms && ` • ${resultData.processing_time_ms.toFixed(0)} мс`}
                    </p>
                </div>
            </div>

            <div className="dist-results-body">
                {/* NLP Quick Summary */}
                <div className="dist-nlp-summary">
                    <div className="dist-nlp-row">
                        <span className="dist-nlp-label">Тип</span>
                        <span className="badge badge-blue">{resultData.nlp_summary.detected_type}</span>
                    </div>
                    <div className="dist-nlp-row">
                        <span className="dist-nlp-label">Тональность</span>
                        <span className={`badge ${resultData.nlp_summary.tonality === 'Негативный' ? 'badge-red' : resultData.nlp_summary.tonality === 'Позитивный' ? 'badge-green' : 'badge-gray'}`}>
                            {resultData.nlp_summary.tonality}
                        </span>
                    </div>
                    <div className="dist-nlp-row">
                        <span className="dist-nlp-label">Приоритет</span>
                        <span className={`badge ${resultData.nlp_summary.priority >= 7 ? 'badge-red' : resultData.nlp_summary.priority >= 4 ? 'badge-orange' : 'badge-green'}`}>
                            {resultData.nlp_summary.priority}/10
                        </span>
                    </div>
                    <div className="dist-nlp-row">
                        <span className="dist-nlp-label">Язык</span>
                        <span className="dist-nlp-value">
                            <Globe size={13} /> {resultData.nlp_summary.language?.toUpperCase()}
                        </span>
                    </div>
                </div>

                {/* Manager Cards */}
                {resultData.assigned_managers.length > 0 ? (
                    <div className="dist-managers-list">
                        {resultData.assigned_managers.map((mgr, idx) => (
                            <ManagerResultCard
                                key={mgr.id}
                                manager={mgr}
                                nlpSummary={resultData.nlp_summary}
                                index={idx}
                                onClick={() => onSelectManager(mgr)}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="dist-empty-state" style={{ minHeight: 120 }}>
                        <p style={{ color: 'var(--accent-orange)' }}>Менеджер не был назначен. Возможно, нет доступных менеджеров в базе.</p>
                    </div>
                )}
            </div>
        </motion.div>
    );
}

/* ── Main Page Component ───────────────────────────── */

export default function DistributionPage() {
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [ticketText, setTicketText] = useState('');
    const [resultData, setResultData] = useState(null);
    const [selectedManager, setSelectedManager] = useState(null);
    const [loadingStep, setLoadingStep] = useState(0);
    const [errorMessage, setErrorMessage] = useState(null);
    const [rawApiResponse, setRawApiResponse] = useState(null);
    const timersRef = useRef([]);

    const handleStart = useCallback(() => {
        setIsPanelOpen(true);
    }, []);

    const clearTimers = useCallback(() => {
        timersRef.current.forEach(clearTimeout);
        timersRef.current = [];
    }, []);

    const handleSubmit = useCallback(async () => {
        if (ticketText.trim().length < 10) return;

        setIsLoading(true);
        setResultData(null);
        setErrorMessage(null);
        setLoadingStep(0);
        clearTimers();

        // Start loading step animation (runs independently)
        LOADING_STEPS.forEach((_, idx) => {
            const timer = setTimeout(
                () => setLoadingStep(idx + 1),
                1200 * (idx + 1)
            );
            timersRef.current.push(timer);
        });

        try {
            // Real API call to backend
            const response = await axios.post(`${API_BASE}/v1/process`, {
                client_guid: `playground-${Date.now()}`,
                description: ticketText,
                segment: 'Mass',
            });

            const data = response.data;
            setRawApiResponse(data);

            // Complete all loading steps
            clearTimers();
            setLoadingStep(LOADING_STEPS.length);

            // Small delay to show final step complete, then show results
            const resultTimer = setTimeout(() => {
                // Map backend response to UI format
                const mapped = {
                    ticket_id: data.ticket_id,
                    status: data.status,
                    processing_time_ms: data.processing_time_ms,
                    nlp_summary: {
                        original_text: ticketText,
                        detected_type: data.analysis?.type || '—',
                        tonality: data.analysis?.tonality || '—',
                        priority: data.analysis?.priority || 0,
                        language: data.analysis?.language || '—',
                        summary: data.analysis?.summary || '',
                        geo_data: {
                            city: data.assigned_manager?.office || '—',
                        },
                    },
                    assigned_managers: data.assigned_manager ? [{
                        id: data.assigned_manager.id,
                        name: data.assigned_manager.name,
                        office: data.assigned_manager.office || '—',
                        position: data.assigned_manager.position || '',
                        skills: data.assigned_manager.skills || [],
                        current_load: data.assigned_manager.current_load ?? 0,
                        max_load: data.assigned_manager.max_load ?? 20,
                        assignment_reason: data.routing_reason || 'Автоматическое назначение алгоритмом F.I.R.E.',
                    }] : [],
                };

                setResultData(mapped);
                setIsLoading(false);
                setLoadingStep(0);
            }, 600);
            timersRef.current.push(resultTimer);

        } catch (err) {
            clearTimers();
            setIsLoading(false);
            setLoadingStep(0);

            const detail = err.response?.data?.detail || err.message || 'Неизвестная ошибка';
            setErrorMessage(`Ошибка API: ${detail}`);
            console.error('Distribution API error:', err);
        }
    }, [ticketText, clearTimers]);

    const handleReset = useCallback(() => {
        setResultData(null);
        setTicketText('');
        setErrorMessage(null);
        setRawApiResponse(null);
    }, []);

    return (
        <div className="dist-playground">
            <AnimatePresence mode="wait">
                {!isPanelOpen ? (
                    <WelcomeState key="welcome" onStart={handleStart} />
                ) : (
                    <motion.div
                        key="workspace"
                        className="dist-workspace"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.3 }}
                    >
                        <div className="dist-split">
                            {/* Left: Input */}
                            <div className="dist-left">
                                <TicketInputForm
                                    ticketText={ticketText}
                                    setTicketText={setTicketText}
                                    onSubmit={handleSubmit}
                                    isLoading={isLoading}
                                />

                                {/* Loading State */}
                                <AnimatePresence>
                                    {isLoading && (
                                        <ProcessingLoader currentStep={loadingStep} />
                                    )}
                                </AnimatePresence>

                                {/* Error */}
                                <AnimatePresence>
                                    {errorMessage && (
                                        <ErrorBanner
                                            message={errorMessage}
                                            onDismiss={() => setErrorMessage(null)}
                                        />
                                    )}
                                </AnimatePresence>

                                {/* Reset Button */}
                                {resultData && !isLoading && (
                                    <motion.button
                                        className="btn btn-secondary dist-reset-btn"
                                        onClick={handleReset}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: 0.5 }}
                                    >
                                        Новый тест
                                    </motion.button>
                                )}
                            </div>

                            {/* Right: Results */}
                            <div className="dist-right">
                                <AnimatePresence>
                                    {resultData && (
                                        <ResultsArea
                                            resultData={resultData}
                                            onSelectManager={setSelectedManager}
                                        />
                                    )}
                                </AnimatePresence>

                                {!resultData && !isLoading && !errorMessage && (
                                    <motion.div
                                        className="dist-empty-state"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: 0.3 }}
                                    >
                                        <div className="dist-empty-icon">
                                            <FlaskConical size={40} />
                                        </div>
                                        <p>Введите текст обращения и запустите анализ, чтобы увидеть результаты</p>
                                    </motion.div>
                                )}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Detail Modal */}
            <AnimatePresence>
                {selectedManager && resultData && (
                    <DetailModal
                        manager={selectedManager}
                        nlpSummary={resultData.nlp_summary}
                        rawApiResponse={rawApiResponse}
                        onClose={() => setSelectedManager(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}
