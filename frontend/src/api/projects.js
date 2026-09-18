import { http } from './client.js';

const RESOURCE = '/projects';

export const projectApi = {
  list: (params) => http.get(RESOURCE, params),
  detail: (id) => http.get(`${RESOURCE}/${id}`),
  create: (payload) => http.post(RESOURCE, payload),
  update: (id, payload) => http.patch(`${RESOURCE}/${id}`, payload),
  remove: (id) => http.delete(`${RESOURCE}/${id}`),
  transitions: (id) => http.get(`${RESOURCE}/${id}/transitions`),
  changeStatus: (id, payload) => http.post(`${RESOURCE}/${id}/transitions`, payload),
  addNode: (id, payload) => http.post(`${RESOURCE}/${id}/nodes`, payload),
  acceptNode: (id, nodeId, payload) => http.patch(`${RESOURCE}/${id}/nodes/${nodeId}`, payload),
  removeNode: (id, nodeId) => http.delete(`${RESOURCE}/${id}/nodes/${nodeId}`),
};
