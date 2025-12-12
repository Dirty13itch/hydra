/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    HYDRA_MCP_URL: process.env.HYDRA_MCP_URL || 'http://192.168.1.244:8600',
  },
}

module.exports = nextConfig
