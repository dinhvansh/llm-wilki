import type { AdminRole, Department, ManagedUser } from '@/lib/types'

import { apiRequest } from './api-client'
import type { IAdminService } from './types'

export function createRealAdminService(): IAdminService {
  return {
    async listUsers() {
      return apiRequest<ManagedUser[]>('/admin/users')
    },
    async createUser(payload) {
      return apiRequest<ManagedUser>('/admin/users', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async updateUser(userId, payload) {
      return apiRequest<ManagedUser>(`/admin/users/${userId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
    },
    async setUserPassword(userId, password) {
      return apiRequest<{ success: boolean; user: ManagedUser }>(`/admin/users/${userId}/set-password`, {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
    },
    async listDepartments() {
      return apiRequest<Department[]>('/admin/departments')
    },
    async createDepartment(payload) {
      return apiRequest<Department>('/admin/departments', {
        method: 'POST',
        body: JSON.stringify(payload),
      })
    },
    async updateDepartment(departmentId, payload) {
      return apiRequest<Department>(`/admin/departments/${departmentId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
    },
    async listRoles() {
      return apiRequest<AdminRole[]>('/admin/roles')
    },
  }
}
