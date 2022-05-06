export default {
    srcDir: 'src/', // Global page headers: https://go.nuxtjs.dev/config-head
    head: {
        title: "代码人生", titleTemplate: "%s | 代码人生", htmlAttrs: {
            lang: 'en'
        }, meta: [{charset: 'utf-8'}, {
            name: 'format-detection', content: 'telephone=no'
        }, {name: 'apple-mobile-web-app-capable', content: 'yes'}, {
            name: 'apple-mobile-web-app-status-bar-style', content: 'black'
        }, {
            name: 'viewport',
            content: 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, minimal-ui'
        }, {name: 'keywords', content: '在线阅读 电子书 下载 推送 程序员书单 人文地理 Kindle epub mobi'}, {
            hid: 'description',
            name: 'description',
            content: '这是个免费的在线书库，基于开源Calibre创建。在这里，你能翻阅喜爱的书籍。同时也能搜索和下载、上传和分享书籍。一个随时随地访问的在线书库！'
        }], link: [{rel: 'shortcut icon', type: 'image/x-icon', href: '/img/favicon.ico'}]
    },

    // Global CSS: https://go.nuxtjs.dev/config-css
    css: ['material-design-icons-iconfont/dist/material-design-icons.css', '@mdi/font/css/materialdesignicons.css'],

    // Plugins to run before rendering page: https://go.nuxtjs.dev/config-plugins
    plugins: ["~/plugins/talebook.js", "~/plugins/load-plugins.js"],

    // Auto import components: https://go.nuxtjs.dev/config-components
    components: true,

    // Modules for dev and build (recommended): https://go.nuxtjs.dev/config-modules
    buildModules: ['@nuxtjs/vuetify', '@nuxtjs/google-fonts'],

    // Modules: https://go.nuxtjs.dev/config-modules
    modules: [],

    // Vuetify module configuration: https://go.nuxtjs.dev/config-vuetify
    vuetify: {
        // treeShake: true,
        defaultAssets: false, iconfont: 'mdi'
    },

    googleFonts: {
        download: true
    },

    publicRuntimeConfig: {
        head: {title: process.env.TITLE || "代码人生", titleTemplate: process.env.TITLE_TEMPLATE || " %s | 代码人生"},
        api_url: process.env.API_URL || "http://127.0.0.1:8000"
    },

    server: {
        port: 9000, // default: 3000
        host: '0.0.0.0' // default: localhost
    },

    // Build Configuration: https://go.nuxtjs.dev/config-build
    build: {
        cache: true, parallel: true
    }
}
