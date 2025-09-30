import { rootRouteWithContext, createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import React from 'react'
import { RootLayout, ChatView, PlaywrightView, ToolsView, SessionsView } from './routes'

// Basic route tree with three tabs
export const rootRoute = createRootRoute({
  component: () => <RootLayout />,
})

export const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <ChatView />,
})

export const playwrightRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/playwright',
  component: () => <PlaywrightView />,
})

export const toolsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/tools',
  component: () => <ToolsView />,
})

export const sessionsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/sessions',
  component: () => <SessionsView />,
})

export const routeTree = rootRoute.addChildren([chatRoute, playwrightRoute, toolsRoute, sessionsRoute])