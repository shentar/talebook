import Vue from 'vue'
import VueRouter from 'vue-router'
Vue.use(VueRouter)

import Vuex from 'vuex'
Vue.use(Vuex)

import '@mdi/font/css/materialdesignicons.css' // Ensure you are using css-loader

import Vuetify from 'vuetify/lib'
import 'vuetify/dist/vuetify.min.css'
Vue.use(Vuetify)

import VueCookies from 'vue-cookies'
Vue.use(VueCookies)

import talebook from './talebook.js'
Vue.use(talebook)

import ActiveSuccess from './pages/ActiveSuccess.vue'
import App           from './App.vue'
import AppAdmin      from './pages/AppAdmin.vue'
import AppIndex      from './pages/AppIndex.vue'
import AppInstall    from './pages/AppInstall.vue'
import AppWelcome    from './pages/AppWelcome.vue'
import BookDetail    from './pages/BookDetail.vue'
import BookEdit      from './pages/BookEdit.vue'
import BookList      from './pages/BookList.vue'
import BookNav       from './pages/BookNav.vue'
import MetaList      from './pages/MetaList.vue'
import NotFound      from './pages/NotFound.vue'
import UserDetail    from './pages/UserDetail.vue'
import UserHistory   from './pages/UserHistory.vue'
import UserLogin     from './pages/UserLogin.vue'
import UserLogout    from './pages/UserLogout.vue'
import UserSignup    from './pages/UserSignup.vue'

Vue.config.productionTip = false

const router = new VueRouter({
    mode: 'history',
    routes: [
        { path: '/',        component: AppIndex   },
        { path: '/nav',     component: BookNav    },
        { path: '/install', component: AppInstall },
        { path: '/search',  component: BookList   },
        { path: '/recent',  component: BookList   },
        { path: '/hot',     component: BookList   },
        { path: '/admin',   component: AppAdmin   },
        { path: '/welcome', component: AppWelcome },
        { path: '/login',   component: UserLogin  },
        { path: '/logout',  component: UserLogout },
        { path: '/signup',  component: UserSignup },

        { path: '/user/detail',    component: UserDetail    },
        { path: '/user/history',   component: UserHistory   },
        { path: '/active/success', component: ActiveSuccess },

        { path: '/book/:bookid(\\d+)', component: BookDetail },
        { path: '/book/:bookid(\\d+)/edit', component: BookEdit },
        { path: '/:meta(publisher|tag|author|rating|series)', component: MetaList },
        { path: '/:meta(publisher|tag|author|rating|series)/:name', component: BookList },

        { path: '*', component: NotFound },
    ]
})

const store = new Vuex.Store({
    state: {
        nav: false,
        loading: true,
        count: 0,
        user: {
            is_admin: false,
            is_login: false,
            nickname: "",
            kindle_email: "",
            avatar: "",
        },
        alert: {
            to: "",
            msg: "",
            type: "",
            show: false,
        },
        sys: {
            socials: [],
            allow: {},
        },
    },
    mutations: {
        loading(state) {
            state.loading = true;
        },
        loaded(state) {
            state.loading = false;
        },
        puremode(state, pure) {
            if ( pure ) {
                state.nav = false;
            } else {
                state.nav = true;
            }
        },
        navbar(state, nav) {
            state.nav = nav;
        },
        increment(state) {
            state.count++
        },
        login(state, data) {
            if ( data != undefined ) {
                state.sys = data.sys;
                state.user = data.user;
            }
        },
        alert(state, v ) {
            state.alert.to = v.to;
            state.alert.type = v.type;
            state.alert.msg = v.msg;
            state.alert.show = true;
        },
        close_alert(state) {
            state.alert.show = false;
        },
    }
})

const vuetify_opts = {
    icons: {
        iconfont: 'mdi',
    },
}


window.app = new Vue({
    vuetify: new Vuetify(vuetify_opts),
    router,
    store,
    render: h => h(App),
}).$mount('#app')

