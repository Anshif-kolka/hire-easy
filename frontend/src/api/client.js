import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const jobsApi = {
  create: (data) => api.post('/job/create', data),
  list: () => api.get('/job/'),
  get: (id) => api.get(`/job/${id}`),
  delete: (id) => api.delete(`/job/${id}`),
  deleteCandidates: (id) => api.delete(`/job/${id}/candidates`),
};

export const resumeApi = {
  upload: (jobId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/resume/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { job_id: jobId },
    });
  },
  list: (jobId) => api.get('/resume/', { params: { job_id: jobId } }),
  listAll: () => api.get('/resume/'),
  get: (id) => api.get(`/resume/${id}`),
  getFull: (id) => api.get(`/resume/${id}/full`),
  triggerEmailIngest: () => api.post('/resume/email-ingest'),
  downloadUrl: (id) => `${api.defaults.baseURL}/resume/${id}/download`,
  delete: (id) => api.delete(`/resume/${id}`),
};

export const rankingApi = {
  getRankings: (jobId, forceRefresh = false) => 
    api.get(`/ranking/${jobId}`, { params: { force_refresh: forceRefresh } }),
  getTopCandidates: (jobId, limit = 5) => 
    api.get(`/ranking/${jobId}/top/${limit}`),
  getCandidateScore: (jobId, candidateId) => 
    api.get(`/ranking/${jobId}/${candidateId}`),
  compare: (jobId, candidateIds) => 
    api.post('/ranking/compare', { job_id: jobId, candidate_ids: candidateIds }),
};

export default api;