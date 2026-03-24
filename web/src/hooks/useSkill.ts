import { useQuery } from '@tanstack/react-query'
import { getSkill, getSkillUsage, getSkillBehavioral, getSkillTimeline } from '@/api/skills'

export function useSkill(slug: string) {
  return useQuery({
    queryKey: ['skill', slug],
    queryFn: () => getSkill(slug),
    enabled: !!slug,
  })
}

export function useSkillUsage(slug: string) {
  return useQuery({
    queryKey: ['skill', slug, 'usage'],
    queryFn: () => getSkillUsage(slug),
    enabled: !!slug,
  })
}

export function useSkillBehavioral(slug: string) {
  return useQuery({
    queryKey: ['skill', slug, 'behavioral'],
    queryFn: () => getSkillBehavioral(slug),
    enabled: !!slug,
  })
}

export function useSkillTimeline(slug: string) {
  return useQuery({
    queryKey: ['skill', slug, 'timeline'],
    queryFn: () => getSkillTimeline(slug),
    enabled: !!slug,
  })
}
