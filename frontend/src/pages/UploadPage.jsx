import { useState, useRef } from 'react';
import { uploadTickets, uploadManagers, uploadBusinessUnits, triggerDistribution } from '../services/api';
import { motion } from 'framer-motion';
import { FileSpreadsheet, Users, Building2, Zap, CheckCircle, AlertCircle } from 'lucide-react';

export default function UploadPage() {
    const [files, setFiles] = useState({ tickets: null, managers: null, units: null });
    const [uploadStatus, setUploadStatus] = useState({ tickets: null, managers: null, units: null });
    const [distributing, setDistributing] = useState(false);
    const [result, setResult] = useState(null);
    const refs = { tickets: useRef(), managers: useRef(), units: useRef() };

    const handleFile = (type) => (e) => {
        const file = e.target.files[0];
        if (file) {
            setFiles(prev => ({ ...prev, [type]: file }));
            setUploadStatus(prev => ({ ...prev, [type]: null }));
        }
    };

    const handleUpload = async (type) => {
        const file = files[type];
        if (!file) return;

        try {
            let res;
            if (type === 'units') {
                res = await uploadBusinessUnits(file);
            } else if (type === 'managers') {
                res = await uploadManagers(file);
            } else {
                res = await uploadTickets(file);
            }
            setUploadStatus(prev => ({ ...prev, [type]: { success: true, message: res.data.message } }));
        } catch (err) {
            const msg = err.response?.data?.detail || err.message;
            setUploadStatus(prev => ({ ...prev, [type]: { success: false, message: msg } }));
        }
    };

    const handleUploadAll = async () => {
        // Upload in order: business units first (for FK), then managers, then tickets
        if (files.units) await handleUpload('units');
        if (files.managers) await handleUpload('managers');
        if (files.tickets) await handleUpload('tickets');
    };

    const handleDistribute = async () => {
        setDistributing(true);
        setResult(null);
        try {
            const res = await triggerDistribution();
            setResult({ success: true, data: res.data });
        } catch (err) {
            setResult({ success: false, message: err.response?.data?.detail || err.message });
        }
        setDistributing(false);
    };

    const cards = [
        { key: 'tickets', label: 'Обращения (Tickets)', desc: 'CSV с данными клиентов и обращений', icon: <FileSpreadsheet size={28} /> },
        { key: 'managers', label: 'Менеджеры (Managers)', desc: 'CSV с ФИО, должностью, навыками', icon: <Users size={28} /> },
        { key: 'units', label: 'Офисы (Business Units)', desc: 'CSV с названиями и адресами офисов', icon: <Building2 size={28} /> },
    ];

    return (
        <>
            <div className="page-header">
                <h2>Загрузка данных</h2>
                <p>Загрузите CSV файлы для анализа и распределения обращений</p>
            </div>

            <div className="upload-grid">
                {cards.map(c => (
                    <motion.div
                        key={c.key}
                        className={`upload-card ${files[c.key] ? 'uploaded' : ''}`}
                        whileHover={{ scale: 1.02 }}
                        onClick={() => refs[c.key].current?.click()}
                    >
                        <div className="upload-icon">{c.icon}</div>
                        <h4>{c.label}</h4>
                        <p>{c.desc}</p>
                        {files[c.key] && (
                            <div className="file-name">
                                <CheckCircle size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
                                {files[c.key].name}
                            </div>
                        )}
                        {uploadStatus[c.key] && (
                            <div style={{ marginTop: 8, fontSize: 12, color: uploadStatus[c.key].success ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                                {uploadStatus[c.key].success ? <CheckCircle size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} /> : <AlertCircle size={12} style={{ marginRight: 4, verticalAlign: 'middle' }} />}
                                {uploadStatus[c.key].message}
                            </div>
                        )}
                        <input
                            type="file"
                            accept=".csv"
                            ref={refs[c.key]}
                            onChange={handleFile(c.key)}
                        />
                    </motion.div>
                ))}
            </div>

            <div className="distribute-section">
                <div style={{ display: 'flex', gap: 16, justifyContent: 'center', flexWrap: 'wrap' }}>
                    <button
                        className="btn btn-secondary"
                        onClick={handleUploadAll}
                        disabled={!files.tickets && !files.managers && !files.units}
                    >
                        <FileSpreadsheet size={18} />
                        Загрузить все файлы
                    </button>
                    <button
                        className="btn btn-success"
                        onClick={handleDistribute}
                        disabled={distributing}
                    >
                        <Zap size={18} />
                        {distributing ? 'Распределение…' : 'Запустить распределение'}
                    </button>
                </div>

                {result && (
                    <motion.div
                        className={`result-panel ${result.success ? 'success' : 'error'}`}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        {result.success ? (
                            <>
                                <strong>✓ Распределение завершено</strong>
                                <p style={{ marginTop: 8 }}>
                                    Обработано: {result.data.total} | Распределено: {result.data.distributed} | Пропущено: {result.data.skipped}
                                </p>
                                {result.data.errors?.length > 0 && (
                                    <details style={{ marginTop: 8 }}>
                                        <summary>Ошибки ({result.data.errors.length})</summary>
                                        <ul style={{ marginTop: 4, paddingLeft: 20, fontSize: 12 }}>
                                            {result.data.errors.map((e, i) => <li key={i}>{e}</li>)}
                                        </ul>
                                    </details>
                                )}
                            </>
                        ) : (
                            <>
                                <strong>✗ Ошибка</strong>
                                <p style={{ marginTop: 8 }}>{result.message}</p>
                            </>
                        )}
                    </motion.div>
                )}
            </div>
        </>
    );
}
