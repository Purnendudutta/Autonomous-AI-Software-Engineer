# Autonomous AI Software Engineer — Frontend 🎨

The modern web dashboard for the Autonomous AI Software Engineer system, built with **React 18**, **TypeScript**, **Vite**, and **Tailwind CSS**.

---

## 🌟 Key Features

* **Interactive Code & Diff Viewer**: Powered by the Monaco Editor (`@monaco-editor/react`) for inspecting repository code and reviewing surgical agent patches.
* **Agent Workflow & Activity Tracker**: Real-time status streaming across architectural planning, code execution, test verification, and security auditing phases.
* **Repository Manager**: Add, inspect, and index local or remote Git repositories.
* **Task Board**: Submit tasks, track self-correction loops in the Docker sandbox, and view compiled Pull Request reports.

---

## 🛠️ Tech Stack

* **Core Framework**: React 18 with TypeScript
* **Build Tool**: Vite 6
* **Styling**: Tailwind CSS & PostCSS
* **Icons**: Lucide React
* **Code Editor**: Monaco Editor
* **HTTP Client**: Axios

---

## 🚀 Getting Started

### 1. Install Dependencies
Make sure you are in the `frontend` directory:
```bash
npm install
```

### 2. Configure Environment Variables
Frontend configuration is read from `.env` in the repository root or defaults to:
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME="Autonomous AI Software Engineer"
```

### 3. Launch Development Server
```bash
npm run dev
```
The dashboard will be available at: **http://localhost:3000**

---

## 📦 Available Scripts

* `npm run dev` — Starts the Vite development server with Hot Module Replacement (HMR).
* `npm run build` — Compiles TypeScript and builds production assets into `dist/`.
* `npm run preview` — Locally previews the production build.
* `npm run type-check` — Runs TypeScript compiler (`tsc --noEmit`) to validate types.
* `npm run lint` — Runs ESLint across all TypeScript and React source files.
