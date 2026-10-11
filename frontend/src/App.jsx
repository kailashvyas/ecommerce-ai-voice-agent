import React, { useState, useEffect } from 'react'
import { fetchProducts } from './services/api.js'
import { ProductGrid } from './components/ProductGrid.jsx'
import { Pagination } from './components/Pagination.jsx'
import VoiceWidget from './components/VoiceWidget.jsx'

export default function App() {
  const [products, setProducts] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalItems, setTotalItems] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Voice Concierge Reactive States
  const [voiceFilteredProducts, setVoiceFilteredProducts] = useState(null)
  const [voiceSearchQuery, setVoiceSearchQuery] = useState('')
  const [orderReceipt, setOrderReceipt] = useState(null)
  const [showReceiptModal, setShowReceiptModal] = useState(false)

  const LIMIT = 6

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    setError(null)

    fetchProducts(page, LIMIT)
      .then((res) => {
        if (!isMounted) return
        setProducts(res.data || [])
        if (res.metadata) {
          setTotalPages(res.metadata.total_pages || 1)
          setTotalItems(res.metadata.total_items || 0)
        }
        setLoading(false)
      })
      .catch((err) => {
        if (!isMounted) return
        console.error('API Fetch Error:', err)
        setError(err.message || 'Failed to fetch products')
        setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [page])

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages && newPage !== page) {
      setPage(newPage)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  // Voice Event Callbacks
  const handleCatalogSearch = (data) => {
    if (!data) return
    const items = Array.isArray(data) ? data : (data.items || data.products || [])
    const query = typeof data === 'object' && data.query ? data.query : ''

    setVoiceFilteredProducts(items)
    setVoiceSearchQuery(query)
  }

  const handleOrderPlaced = (data) => {
    if (!data) return
    const order = data.order || data
    setOrderReceipt(order)
    setShowReceiptModal(true)
  }

  const clearVoiceFilter = () => {
    setVoiceFilteredProducts(null)
    setVoiceSearchQuery('')
  }

  const displayProducts = voiceFilteredProducts !== null ? voiceFilteredProducts : products
  const isVoiceFiltered = voiceFilteredProducts !== null

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">Product Catalog</h1>
        <p className="app-subtitle">
          Explore our collection ({isVoiceFiltered ? displayProducts.length : totalItems} {isVoiceFiltered ? 'matched' : 'total'} items)
        </p>
      </header>

      {isVoiceFiltered && (
        <div className="voice-filter-banner" style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#eff6ff',
          border: '1px solid #bfdbfe',
          color: '#1e40af',
          padding: '0.75rem 1.25rem',
          borderRadius: '8px',
          marginBottom: '1.5rem'
        }}>
          <span>
            🎤 <strong>Voice Search:</strong> Showing results for "{voiceSearchQuery}" ({displayProducts.length} items)
          </span>
          <button
            onClick={clearVoiceFilter}
            style={{
              background: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              padding: '0.35rem 0.75rem',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem'
            }}
          >
            Clear Search
          </button>
        </div>
      )}

      <main>
        <ProductGrid products={displayProducts} loading={loading && !isVoiceFiltered} error={error} />
        {!loading && !error && !isVoiceFiltered && (
          <Pagination
            currentPage={page}
            totalPages={totalPages}
            onPageChange={handlePageChange}
          />
        )}
      </main>

      {/* Floating Voice Concierge Widget */}
      <VoiceWidget
        onCatalogSearch={handleCatalogSearch}
        onOrderPlaced={handleOrderPlaced}
      />

      {/* Order Confirmation Receipt Modal */}
      {showReceiptModal && orderReceipt && (
        <div className="modal-overlay" style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.65)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(4px)'
        }}>
          <div className="modal-content" style={{
            background: '#ffffff',
            borderRadius: '12px',
            padding: '2rem',
            maxWidth: '480px',
            width: '90%',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)',
            position: 'relative'
          }}>
            <button
              onClick={() => setShowReceiptModal(false)}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
                border: 'none',
                background: 'transparent',
                fontSize: '1.5rem',
                cursor: 'pointer',
                color: '#64748b'
              }}
            >
              ×
            </button>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🎉</div>
              <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a' }}>Order Placed!</h2>
              <p style={{ color: '#64748b', fontSize: '0.95rem' }}>Your order has been confirmed.</p>
            </div>

            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              padding: '1.25rem',
              marginBottom: '1.5rem'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <span style={{ color: '#64748b' }}>Customer Name:</span>
                <strong style={{ color: '#0f172a' }}>{orderReceipt.customer_name || 'Valued Customer'}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <span style={{ color: '#64748b' }}>Product Title:</span>
                <strong style={{ color: '#0f172a', textAlign: 'right', maxWidth: '240px' }}>{orderReceipt.product_title || 'Product'}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <span style={{ color: '#64748b' }}>Quantity:</span>
                <strong style={{ color: '#0f172a' }}>{orderReceipt.quantity || 1}</strong>
              </div>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                paddingTop: '0.75rem',
                borderTop: '1px solid #cbd5e1',
                marginTop: '0.75rem'
              }}>
                <span style={{ color: '#0f172a', fontWeight: 600 }}>Total Price:</span>
                <strong style={{ color: '#2563eb', fontSize: '1.25rem' }}>
                  ${typeof orderReceipt.total_price === 'number' ? orderReceipt.total_price.toFixed(2) : (orderReceipt.total_price || '0.00')}
                </strong>
              </div>
            </div>

            <button
              onClick={() => setShowReceiptModal(false)}
              style={{
                width: '100%',
                background: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '0.75rem',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
