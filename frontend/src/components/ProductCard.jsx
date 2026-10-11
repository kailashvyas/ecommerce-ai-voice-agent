import React, { useState } from 'react'

export function ProductCard({ product }) {
  const [imgError, setImgError] = useState(false)

  const formattedPrice = typeof product.price === 'number'
    ? `$${product.price.toFixed(2)}`
    : `$${product.price}`

  return (
    <div className="product-card">
      <div className="product-image-container">
        {!imgError && product.image ? (
          <img
            src={product.image}
            alt={product.title}
            className="product-image"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="product-image-fallback" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8', fontSize: '0.875rem' }}>
            <span>No Image</span>
          </div>
        )}
        {product.category && (
          <span className="product-category-tag">{product.category}</span>
        )}
      </div>

      <div className="product-info">
        <h3 className="product-title">{product.title}</h3>
        {product.description && (
          <p className="product-description">{product.description}</p>
        )}
        <div className="product-footer">
          <span className="product-price">{formattedPrice}</span>
        </div>
      </div>
    </div>
  )
}

export default ProductCard
