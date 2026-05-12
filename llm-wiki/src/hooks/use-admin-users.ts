'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { adminService } from '@/services'

export function useAdminUsers() {
  return useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminService.listUsers(),
  })
}

export function useAdminDepartments() {
  return useQuery({
    queryKey: ['admin-departments'],
    queryFn: () => adminService.listDepartments(),
  })
}

export function useAdminRoles() {
  return useQuery({
    queryKey: ['admin-roles'],
    queryFn: () => adminService.listRoles(),
  })
}

export function useAdminUserActions() {
  const queryClient = useQueryClient()

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    await queryClient.invalidateQueries({ queryKey: ['admin-departments'] })
  }

  const createUser = useMutation({
    mutationFn: (payload: { email: string; name: string; role: string; password: string; departmentId?: string | null; isActive?: boolean }) => adminService.createUser(payload),
    onSuccess: refresh,
  })

  const updateUser = useMutation({
    mutationFn: ({ userId, payload }: { userId: string; payload: { email?: string; name?: string; role?: string; departmentId?: string | null; isActive?: boolean } }) => adminService.updateUser(userId, payload),
    onSuccess: refresh,
  })

  const setPassword = useMutation({
    mutationFn: ({ userId, password }: { userId: string; password: string }) => adminService.setUserPassword(userId, password),
    onSuccess: refresh,
  })

  const createDepartment = useMutation({
    mutationFn: (payload: { name: string; description?: string }) => adminService.createDepartment(payload),
    onSuccess: refresh,
  })

  const updateDepartment = useMutation({
    mutationFn: ({ departmentId, payload }: { departmentId: string; payload: { name?: string; description?: string } }) => adminService.updateDepartment(departmentId, payload),
    onSuccess: refresh,
  })

  return { createUser, updateUser, setPassword, createDepartment, updateDepartment }
}
