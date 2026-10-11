const API_BASE = '/api'

export async function fetchProducts(page = 1, limit = 6) {
  const url = `${API_BASE}/products?page=${page}&limit=${limit}`
  try {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to fetch products: ${response.status} ${response.statusText}`)
    }
    const data = await response.json()
    return data
  } catch (err) {
    // Fallback attempt for direct backend port if proxy is not active
    if (url.startsWith('/api')) {
      const fallbackUrl = `http://localhost:8000/api/products?page=${page}&limit=${limit}`
      const response = await fetch(fallbackUrl)
      if (!response.ok) {
        throw new Error(`Failed to fetch products: ${response.status} ${response.statusText}`)
      }
      return await response.json()
    }
    throw err
  }
}
