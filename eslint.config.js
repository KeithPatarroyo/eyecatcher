const js = require("@eslint/js");
const globals = require("globals");
const prettier = require("eslint-config-prettier");

module.exports = [
    { ignores: ["node_modules/", "dist/", "*.min.js", "eslint.config.js"] },
    js.configs.recommended,
    {
        files: ["static/**/*.js"],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "module",
            globals: {
                ...globals.browser,
                AppCore: "readonly",
                ApiClient: "readonly",
                PatternRenderer: "readonly",
                AnimationLoop: "readonly",
                PopulationUI: "readonly",
                Storage: "readonly",
                ToolbarUI: "readonly",
                Toast: "readonly",
                Utils: "readonly",
                showLoading: "readonly",
                ViewerControls: "readonly",
                Community: "readonly",
                NetworkVisualizer: "readonly",
                DOM: "readonly",
                Debug: "readonly",
                JSZip: "readonly",
                vis: "readonly",
                showToast: "readonly",
                module: "readonly",
            },
        },
        rules: {
            "no-unused-vars": [
                "warn",
                {
                    argsIgnorePattern: "^_",
                    varsIgnorePattern: "^_",
                    caughtErrorsIgnorePattern: "^_",
                },
            ],
            "no-undef": "error",
            eqeqeq: ["warn", "smart"],
            "no-console": "off",
        },
    },
    prettier,
];
