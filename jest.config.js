module.exports = {
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/tests/frontend/setup.js'],
    moduleNameMapper: {
        '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
        '\\.(gif|ttf|eot|svg)$': '<rootDir>/tests/frontend/__mocks__/fileMock.js'
    },
    testMatch: [
        '<rootDir>/tests/frontend/**/*.test.js'
    ],
    transform: {
        '^.+\\.js$': 'babel-jest'
    },
    collectCoverage: true,
    coverageDirectory: 'coverage',
    coverageReporters: ['text', 'lcov'],
    collectCoverageFrom: [
        'src/static/js/**/*.js',
        '!src/static/js/vendor/**/*.js'
    ]
}; 