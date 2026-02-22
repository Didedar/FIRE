import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE,
});

export const uploadTickets = (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/upload/tickets', fd);
};

export const uploadManagers = (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/upload/managers', fd);
};

export const uploadBusinessUnits = (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post('/upload/business-units', fd);
};

export const triggerDistribution = () => api.post('/distribute');

export const getTickets = (params) => api.get('/tickets', { params });
export const getTicket = (id) => api.get(`/tickets/${id}`);
export const getManagers = () => api.get('/managers');
export const getOffices = () => api.get('/managers/offices');
export const getStats = () => api.get('/stats');
export const askAI = (query) => api.post('/ai-assistant', { query });

// Deletion endpoints
export const deleteTicket = (id) => api.delete(`/tickets/${id}`);
export const deleteAllTickets = () => api.delete('/tickets');

export const deleteManager = (id) => api.delete(`/managers/${id}`);
export const deleteAllManagers = () => api.delete('/managers');

export const deleteOffice = (id) => api.delete(`/managers/offices/${id}`);
export const deleteAllOffices = () => api.delete('/managers/offices');

export default api;
