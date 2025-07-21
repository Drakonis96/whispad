export default {
  transform: {
    '^.+\\.(ts|tsx)$': 'ts-jest'
  },
  testEnvironment: 'jsdom',
  moduleNameMapper: {
    '^(.*)\\?worker$': '$1'
  },
  roots: ['tests'],
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts']
};
