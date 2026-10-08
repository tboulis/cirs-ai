# CIRS-Agent Frontend

React frontend for the Critical Infrastructure Resilience Support chatbot.

## Features

- Modern React 18 with TypeScript
- Tailwind CSS for styling
- Real-time chat interface with markdown support
- Document upload and management
- Multi-model LLM support
- Conversation history
- Responsive design
- Dark/light theme support

## Tech Stack

- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type safety and better developer experience
- **Tailwind CSS** - Utility-first CSS framework
- **React Query** - Data fetching and caching
- **React Router** - Client-side routing
- **Lucide React** - Beautiful icons
- **React Markdown** - Markdown rendering
- **React Syntax Highlighter** - Code syntax highlighting
- **React Hot Toast** - Toast notifications
- **Zustand** - Simple state management
- **Axios** - HTTP client

## Getting Started

### Prerequisites

- Node.js 16+ and npm
- Backend API running on port 8000

### Installation

1. Navigate to the frontend directory:

    ```bash
    cd frontend
    ```

2. Install dependencies:

    ```bash
    npm install
    ```

3. Start the development server (Vite):

    ```bash
    npm start
    ```

The app will open at [http://localhost:3000](http://localhost:3000). The dev server proxies `/api` to `http://localhost:8000` (see `vite.config.ts`).

### Available Scripts

- `npm start` - Start Vite development server
- `npm run build` - Build for production (outputs to `dist/`)
- `npm run preview` - Preview the production build locally

## Project Structure

```bash
frontend/
├── index.html              # Vite HTML entry
├── public/                 # Static assets
│   └── manifest.json       # PWA manifest
├── src/
│   ├── components/         # React components
│   ├── pages/              # Page components
│   ├── services/           # API services
│   ├── types/              # TypeScript type definitions
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Vite entry point
│   └── index.css           # Global styles
├── vite.config.ts          # Vite configuration
├── package.json            # Dependencies and scripts
├── tailwind.config.js      # Tailwind configuration
├── tsconfig.json           # TypeScript configuration
└── README.md               # This file
```

## Key Components

### ChatLayout

Main layout component with sidebar and chat interface.

### ChatInterface

Core chat functionality with message display and input.

### Sidebar

Navigation and conversation history management.

### DocumentsPage

Document upload and management interface.

### SettingsPage

Configuration and system settings.

## API Integration

The frontend communicates with the FastAPI backend through:

- **Chat API** - Send messages, manage conversations
- **Document API** - Upload, process, and search documents
- **System API** - Health checks and model information

All API calls are typed with TypeScript interfaces.

## Styling

Uses Tailwind CSS with a custom design system:

- **Primary Colors** - Blue theme for main actions
- **Secondary Colors** - Gray theme for text and backgrounds
- **Status Colors** - Success, warning, and error states
- **Typography** - Inter font family
- **Components** - Custom button, input, and card styles

## State Management

- **React Query** - Server state and caching
- **Local State** - Component state with useState
- **Context** - Minimal global state where needed

## Deployment

### Build for Production

```bash
npm run build
```

This creates an optimized build in the `dist/` directory.

### Environment Variables

Vite uses the `VITE_` prefix for env vars (available via `import.meta.env`). Example `.env`:

```env
VITE_API_URL=http://localhost:8000
VITE_APP_VERSION=1.0.0
```

By default the app calls relative `/api/v1/...` paths and the dev proxy forwards them to the backend, so you typically do not need to configure `VITE_API_URL` for development.

### Docker Deployment

```dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Development

### Code Style

- ESLint for code linting
- Prettier for code formatting
- TypeScript strict mode enabled

### Component Guidelines

- Use functional components with hooks
- Implement proper TypeScript typing
- Follow React Query patterns for data fetching
- Use Tailwind utility classes for styling

### Testing

```bash
npm test
```

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Write tests for new components
4. Update documentation as needed

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Performance

- Code splitting with React.lazy()
- React Query for efficient data fetching
- Optimized bundle size with tree shaking
- Service worker for caching (in production)

## Troubleshooting

### Common Issues

1. **Module not found errors**: Run `npm install`
2. **API connection issues / Vite proxy errors**: Ensure backend is running on `http://localhost:8000`.
   - If you see `connect ECONNREFUSED ::1:8000`, change the proxy to IPv4 in `vite.config.ts`:

    ```ts
    export default defineConfig({
    server: {
        proxy: {
        '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
        },
    },
    });
    ```

3. **CSS import order warning**: Move external `@import` lines to the very top of `src/index.css` (before Tailwind directives).
4. **Build failures**: Clear node_modules and reinstall
5. **Style issues**: Rebuild Tailwind CSS

### Debug Mode

Set `NODE_ENV=development` for additional debug information.

## License

MIT License
