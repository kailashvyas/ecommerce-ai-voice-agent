import React from 'react'
import { ProductCard } from './ProductCard.jsx'

export function ProductGrid({ products, loading, error }) {
  if (loading) {
    return (
      <div className="status-container">
        <div className="loading-spinner"></div>
        <p>Loading products...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="status-container">
        <div className="error-message">
          <p><strong>Error loading catalog:</strong> {error}</p>
        </div>
      </div>
    )
  }

  if (!products || products.length === 0) {
    return (
      <div className="status-container">
        <p>No products available.</p>
      </div>
    )
  }

  return (
    <div className="product-grid">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  )
}

export default ProductGrid
