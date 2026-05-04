// Service exports - swap these imports to switch from mock to real API
export {
  createMockDashboardService as dashboardServiceFactory,
  createMockSourceService as sourceServiceFactory,
  createMockPageService as pageServiceFactory,
  createMockReviewService as reviewServiceFactory,
  createMockQueryService as queryServiceFactory,
  createMockGraphService as graphServiceFactory,
} from './mock'

import {
  createMockDashboardService,
  createMockCollectionService,
  createMockDiagramService,
  createMockGraphService,
  createMockLintService,
  createMockPageService,
  createMockQueryService,
  createMockReviewService,
  createMockSettingsService,
  createMockSourceService,
} from './mock'
import { createRealCollectionService } from './real-collections'
import { createRealDiagramService } from './real-diagrams'
import { createRealDashboardService } from './real-dashboard'
import { createRealGraphService } from './real-graph'
import { createRealLintService } from './real-lint'
import { createRealPageService } from './real-pages'
import { createRealQueryService } from './real-query'
import { createRealReviewService } from './real-review'
import { createRealSettingsService } from './real-settings'
import { createRealSourceService } from './real-sources'

const useRealApi = process.env.NEXT_PUBLIC_USE_REAL_API !== 'false'

export const dashboardService = useRealApi ? createRealDashboardService() : createMockDashboardService()
export const collectionService = useRealApi ? createRealCollectionService() : createMockCollectionService()
export const diagramService = useRealApi ? createRealDiagramService() : createMockDiagramService()
export const sourceService = useRealApi ? createRealSourceService() : createMockSourceService()
export const pageService = useRealApi ? createRealPageService() : createMockPageService()
export const reviewService = useRealApi ? createRealReviewService() : createMockReviewService()
export const queryService = useRealApi ? createRealQueryService() : createMockQueryService()
export const graphService = useRealApi ? createRealGraphService() : createMockGraphService()
export const lintService = useRealApi ? createRealLintService() : createMockLintService()
export const settingsService = useRealApi ? createRealSettingsService() : createMockSettingsService()

export type { ICollectionService, IDashboardService, IDiagramService, IGraphService, ILintService, IPageService, IQueryService, IReviewService, ISettingsService, ISourceService } from './types'
