import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { transformSync } from 'esbuild'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

console.log('Building frontend catalog application for production...')

const distDir = path.join(__dirname, 'dist')
const assetsDir = path.join(distDir, 'assets')

// 1. Ensure clean dist directory handling ENOTEMPTY/EBUSY safely
function cleanDistDir() {
  if (fs.existsSync(distDir)) {
    try {
      fs.rmSync(distDir, { recursive: true, force: true })
    } catch (err) {
      if (err.code === 'ENOTEMPTY' || err.code === 'EBUSY' || err.code === 'EPERM') {
        try {
          const entries = fs.readdirSync(distDir)
          for (const entry of entries) {
            fs.rmSync(path.join(distDir, entry), { recursive: true, force: true })
          }
        } catch (_) {}
      } else {
        throw err
      }
    }
  }
  fs.mkdirSync(assetsDir, { recursive: true })
}

cleanDistDir()

// Helper to safely read required component file
function readRequiredFile(filePath, name) {
  if (!fs.existsSync(filePath)) {
    console.error(`Error: Required file ${name} missing at ${filePath}`)
    process.exit(1)
  }
  return fs.readFileSync(filePath, 'utf-8')
}

// Helper to collapse multi-line React.createElement calls onto single lines
function flattenCreateElement(code) {
  const lines = code.split('\n')
  let result = ''
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.includes('React.createElement')) {
      let buffer = line
      let openP = (buffer.match(/\(/g) || []).length
      let closeP = (buffer.match(/\)/g) || []).length
      while (openP > closeP && i + 1 < lines.length) {
        i++
        const nextLine = lines[i].trim()
        buffer += ' ' + nextLine
        openP += (nextLine.match(/\(/g) || []).length
        closeP += (nextLine.match(/\)/g) || []).length
      }
      result += buffer + '\n'
    } else {
      result += line + '\n'
    }
  }
  return result
}

// 2. Transpile JSX syntax to standard React.createElement
function transpileJSX(code) {
  let result = code

  // Remove import statements to avoid unresolved local module imports in combined bundle
  result = result.replace(/import\s+React\s*(?:,\s*\{[^}]*\}|\{[^}]*\})?\s*from\s*['"][^'"]+['"]/g, '')
  result = result.replace(/import\s+\{[^}]*\}\s*from\s*['"][^'"]+['"]/g, '')
  result = result.replace(/import\s+[A-Za-z0-9_]+\s+from\s*['"][^'"]+['"]/g, '')

  // Handle exports so function declarations remain literal
  result = result.replace(/export\s+default\s+function\b/g, 'function')
  result = result.replace(/export\s+function\b/g, 'function')
  result = result.replace(/export\s+default\s+class\b/g, 'class')
  result = result.replace(/export\s+class\b/g, 'class')
  result = result.replace(/export\s+default\s+[A-Za-z0-9_]+\s*;?/g, '')

  const transpiled = transformSync(result, {
    loader: 'jsx',
    jsx: 'transform',
    jsxFactory: 'React.createElement',
    jsxFragment: 'React.Fragment'
  })

  return flattenCreateElement(transpiled.code)
}

try {
  // Read index.css
  const cssContent = fs.readFileSync(path.join(__dirname, 'src', 'index.css'), 'utf-8')
  fs.writeFileSync(path.join(assetsDir, 'index.css'), cssContent)

  // Read index.html
  let htmlContent = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf-8')
  htmlContent = htmlContent.replace(
    '<script type="module" src="/src/main.jsx"></script>',
    '<link rel="stylesheet" href="/assets/index.css">\n    <script type="module" src="/assets/index.js"></script>'
  )
  fs.writeFileSync(path.join(distDir, 'index.html'), htmlContent)

  // Read required components
  let apiCode = readRequiredFile(path.join(__dirname, 'src', 'services', 'api.js'), 'api.js')
  apiCode = apiCode.replace(/export\s+async\s+function\b/g, 'async function')
  apiCode = apiCode.replace(/export\s+function\b/g, 'function')

  const cardCode = readRequiredFile(path.join(__dirname, 'src', 'components', 'ProductCard.jsx'), 'ProductCard.jsx')
  const gridCode = readRequiredFile(path.join(__dirname, 'src', 'components', 'ProductGrid.jsx'), 'ProductGrid.jsx')
  const pageCode = readRequiredFile(path.join(__dirname, 'src', 'components', 'Pagination.jsx'), 'Pagination.jsx')
  const appCode = readRequiredFile(path.join(__dirname, 'src', 'App.jsx'), 'App.jsx')

  const voiceWidgetPath = path.join(__dirname, 'src', 'components', 'VoiceWidget.jsx')
  const voiceCode = fs.existsSync(voiceWidgetPath) ? fs.readFileSync(voiceWidgetPath, 'utf-8') : ''

  // Build single-file module bundle
  const appJsContent = `import React, { useState, useEffect, useRef } from 'https://esm.sh/react@18'
import ReactDOM from 'https://esm.sh/react-dom@18/client'

// API Service
${apiCode}

// Components
${transpileJSX(cardCode)}
${transpileJSX(gridCode)}
${transpileJSX(pageCode)}
${voiceCode ? transpileJSX(voiceCode) : 'function VoiceWidget() { return null }'}
${transpileJSX(appCode)}

// Main Entry Point
const rootEl = document.getElementById('root')
if (rootEl) {
  ReactDOM.createRoot(rootEl).render(
    React.createElement(React.StrictMode, null, React.createElement(App, null))
  )
}
`

  fs.writeFileSync(path.join(assetsDir, 'index.js'), appJsContent)
  console.log('✓ Build completed successfully! Output generated in frontend/dist.')
  process.exit(0)
} catch (err) {
  console.error('Build error:', err)
  process.exit(1)
}
