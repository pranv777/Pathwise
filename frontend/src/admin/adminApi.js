import axios from 'axios'
import { friendlyError } from '../utils/errors.js'

// Own instance: the shared client's default export is the helper object, and its
// 401 handler reloads the page, which is wrong for an admin 403.
const http = axios.create({
  baseURL: '/api/admin',
  withCredentials: true,
  timeout: 30000,
})
const data = (r) => r.data

export const adminApi = {
  overview: (days = 14) => http.get('/overview', { params: { days } }).then(data),
  students: (params) => http.get('/students', { params }).then(data),
  student: (id) => http.get(`/students/${id}`).then(data),
  setStudentStatus: (id, status) => http.patch(`/students/${id}/status`, { status }).then(data),
  deleteStudent: (id) => http.delete(`/students/${id}`),
  studentsCsvUrl: (params) => `/api/admin/students/export.csv?${new URLSearchParams(params)}`,
  drives: () => http.get('/drives').then(data),
  saveDrive: (d) => (d.id ? http.put(`/drives/${d.id}`, d) : http.post('/drives', d)).then(data),
  deleteDrive: (id) => http.delete(`/drives/${id}`),
  agents: () => http.get('/agents').then(data),
  runs: (params) => http.get('/runs', { params }).then(data),
  kb: () => http.get('/kb').then(data),
  kbUpload: (docType, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http
      .post('/kb', fd, {
        params: { doc_type: docType },
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000,
      })
      .then(data)
  },
  kbDelete: (source) => http.delete('/kb', { params: { source } }),
  kbReseed: () => http.post('/kb/reseed', null, { timeout: 120000 }).then(data),
  mcp: () => http.get('/mcp').then(data),
  audit: (params) => http.get('/audit', { params }).then(data),
}

export const errMsg = (e) => friendlyError(e)
