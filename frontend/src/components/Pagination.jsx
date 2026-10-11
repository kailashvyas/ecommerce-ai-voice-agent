import React from 'react'

export function Pagination({ currentPage, totalPages, onPageChange }) {
  if (totalPages <= 1) return null

  const pageNumbers = []
  for (let i = 1; i <= totalPages; i++) {
    pageNumbers.push(i)
  }

  const handlePrev = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1)
    }
  }

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1)
    }
  }

  return (
    <nav className="pagination-container" aria-label="Product Catalog Pagination">
      <button
        type="button"
        className="pagination-btn"
        onClick={handlePrev}
        disabled={currentPage <= 1}
        aria-label="Previous page"
      >
        Previous
      </button>

      {pageNumbers.map((page) => (
        <button
          key={page}
          type="button"
          className={`pagination-btn ${page === currentPage ? 'active' : ''}`}
          onClick={() => onPageChange(page)}
          aria-label={`Page ${page}`}
          aria-current={page === currentPage ? 'page' : undefined}
        >
          {page}
        </button>
      ))}

      <button
        type="button"
        className="pagination-btn"
        onClick={handleNext}
        disabled={currentPage >= totalPages}
        aria-label="Next page"
      >
        Next
      </button>
    </nav>
  )
}

export default Pagination
