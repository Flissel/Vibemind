import { rootRouteWithContext, createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import React from 'react'
import { RootLayout, ChatView, ToolsView, SessionsView, SecretsView } from './routes'

// Basic route tree with three tabs
export const rootRoute = createRootRoute({
  component: () => <RootLayout />,
})

export const chatRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: () => <ChatView />,
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

export const secretsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/secrets',
  component: () => <SecretsView />,
})

export const routeTree = rootRoute.addChildren([chatRoute, toolsRoute, sessionsRoute, secretsRoute])