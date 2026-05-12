import type { AdminRole, Department, ManagedUser } from '@/lib/types'

import type { IAdminService } from '../types'

const MOCK_USERS: ManagedUser[] = [
  {
    id: 'user-dev-admin',
    email: 'admin@local.test',
    name: 'Dev Admin',
    role: 'admin',
    permissions: ['*'],
    scopeMode: 'all',
    accessibleCollectionIds: [],
    collectionMemberships: [],
    isActive: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
]

const MOCK_DEPARTMENTS: Department[] = [
  { id: 'dept-eng', name: 'Engineering', slug: 'engineering', description: 'Platform and product delivery.', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
  { id: 'dept-ops', name: 'Operations', slug: 'operations', description: 'Knowledge operations and review.', createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() },
]

const MOCK_ROLES: AdminRole[] = [
  { id: 'reader', name: 'Reader', slug: 'reader', description: 'Browse and ask against allowed knowledge.', permissions: ['collection:read', 'source:read', 'page:read', 'graph:read', 'ask:read'], isSystem: true },
  { id: 'editor', name: 'Editor', slug: 'editor', description: 'Edit sources, pages, and structured knowledge assets.', permissions: ['collection:write', 'source:write', 'page:write', 'diagram:write'], isSystem: true },
  { id: 'reviewer', name: 'Reviewer', slug: 'reviewer', description: 'Review, approve, and govern knowledge workflows.', permissions: ['review:read', 'review:approve', 'lint:read', 'settings:read'], isSystem: true },
  { id: 'admin', name: 'Admin', slug: 'admin', description: 'Full system access, settings, and people management.', permissions: ['*'], isSystem: true },
]

export function createMockAdminService(): IAdminService {
  return {
    async listUsers() {
      return MOCK_USERS
    },
    async createUser(payload) {
      const user: ManagedUser = {
        id: `mock-user-${Date.now()}`,
        email: payload.email,
        name: payload.name,
        role: payload.role,
        departmentId: payload.departmentId ?? null,
        departmentName: MOCK_DEPARTMENTS.find(item => item.id === payload.departmentId)?.name ?? null,
        permissions: [],
        scopeMode: 'all',
        accessibleCollectionIds: [],
        collectionMemberships: [],
        isActive: payload.isActive ?? true,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      MOCK_USERS.push(user)
      return user
    },
    async updateUser(userId, payload) {
      const user = MOCK_USERS.find(item => item.id === userId) ?? MOCK_USERS[0]
      Object.assign(user, payload, {
        departmentName: payload.departmentId === undefined ? user.departmentName : (MOCK_DEPARTMENTS.find(item => item.id === payload.departmentId)?.name ?? null),
        updatedAt: new Date().toISOString(),
      })
      return user
    },
    async setUserPassword(userId) {
      const user = MOCK_USERS.find(item => item.id === userId) ?? MOCK_USERS[0]
      user.updatedAt = new Date().toISOString()
      return { success: true, user }
    },
    async listDepartments() {
      return MOCK_DEPARTMENTS
    },
    async createDepartment(payload) {
      const department: Department = {
        id: `dept-${Date.now()}`,
        name: payload.name,
        slug: payload.name.toLowerCase().replace(/\W+/g, '-').replace(/^-|-$/g, ''),
        description: payload.description ?? '',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }
      MOCK_DEPARTMENTS.push(department)
      return department
    },
    async updateDepartment(departmentId, payload) {
      const department = MOCK_DEPARTMENTS.find(item => item.id === departmentId) ?? MOCK_DEPARTMENTS[0]
      Object.assign(department, payload, { updatedAt: new Date().toISOString() })
      if (payload.name) {
        department.slug = payload.name.toLowerCase().replace(/\W+/g, '-').replace(/^-|-$/g, '')
      }
      return department
    },
    async listRoles() {
      return MOCK_ROLES
    },
  }
}
