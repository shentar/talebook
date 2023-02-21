export const state = () => ({
    nav: true, loading: true, count: 0, user: {
        is_admin: false, is_login: false, is_active: false, nickname: "", pems: "", kindle_email: "", avatar: "",
    }, alert: {
        to: "", msg: "", type: "", show: false,
    }, sys: {
        socials: [], allow: {},
    },
})

export const mutations = {
    loading(state) {
        state.loading = true;
    }, loaded(state) {
        state.loading = false;
    }, /*
    puremode(state, pure) {
        if (pure) {
            state.nav = false;
        } else {
            state.nav = true;
        }
    },
    */
    navbar(state, nav) {
        state.nav = nav;
    }, increment(state) {
        state.count++
    }, login(state, data) {
        if (data !== undefined) {
            state.sys = data.sys;
            state.user = data.user;
        }
    }, alert(state, v) {
        state.alert.to = v.to;
        state.alert.type = v.type;
        state.alert.msg = v.msg;
        state.alert.show = true;
        if (state.alert.type === 'success') {
            setTimeout(() => state.alert.show = false, 1300)
        }
    }, close_alert(state) {
        state.alert.show = false;
    },
}