// frontend-tester/jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^lib/firebase$': '<rootDir>/lib/firebase',
    '^src/context/AuthContext$': '<rootDir>/src/context/AuthContext',
  },
  transform: {
    '^.+\.(t|j)sx?$': ['@swc/jest', {
      jsc: {
        transform: {
          react: {
            runtime: 'automatic',
          },
        },
      },
    }],
  },
};
