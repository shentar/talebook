<template>
    <v-row justify=center class="fill-center">
        <v-col xs=12 sm=8 md=4>
            <v-card class="elevation-12">
                <v-toolbar dark color="primary">
                    <v-toolbar-title>填写注册信息</v-toolbar-title>
                </v-toolbar>
                <v-card-text>
                    <v-form ref="form" @submit.prevent="signup">
                        <v-text-field required prepend-icon="person" v-model="username" label="用户名" type="text"
                                      autocomplete="new-username" :rules="[rules.user]"></v-text-field>
                        <v-text-field required prepend-icon="lock" v-model="password" label="密码" type="password"
                                      autocomplete="new-password" :rules="[rules.pass]"></v-text-field>
                        <v-text-field required prepend-icon="lock" v-model="password2" label="确认密码" type="password"
                                      autocomplete="new-password2" :rules="[valid]"></v-text-field>
                        <v-text-field required prepend-icon="face" v-model="nickname" label="昵称" type="text"
                                      autocomplete="new-nickname" :rules="[rules.nick]"></v-text-field>
                        <v-text-field required prepend-icon="email" v-model="email" label="Email(用于接收激活链接)"
                                      type="text"
                                      autocomplete="new-email" :rules="[rules.email]"></v-text-field>
                    </v-form>
                    <div align="center">
                        <v-btn dark large rounded color="red" @click="signup">注册</v-btn>
                    </div>
                </v-card-text>

                <v-alert v-if="failmsg" type="error">{{ failmsg }}</v-alert>
            </v-card>
        </v-col>
    </v-row>
</template>

<script>
export default {
    created() {
        this.$store.commit("navbar", false);
    },
    data: () => ({
        username: "",
        password: "",
        password2: "",
        nickname: "",
        email: "",
        failmsg: "",
        validmsg: "",
        rules: {
            user: v => (12 >= v.length && v.length >= 3) || '3 ~ 12 characters',
            pass: v => (16 >= v.length && v.length >= 6) || '6 ~ 16 characters',
            nick: v => v.length >= 2 || 'Min 2 characters',
            email: function (email) {
                var re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
                return re.test(email) || "Invalid email format";
            },
        },

    }),
    head: () => ({
        title: "注册",
    }),
    methods: {
        valid: function (v) {
            return v === this.password || "Password are not same."
        },
        signup: function () {
            if (!this.$refs.form.validate()) {
                return false;
            }

            var data = new URLSearchParams();
            data.append('username', this.username);
            data.append('password', this.password);
            data.append('nickname', this.nickname);
            data.append('email', this.email);
            this.$backend('/user/sign_up', {
                method: 'POST',
                body: data,
            }).then(rsp => {
                if (rsp.err !== 'ok') {
                    this.failmsg = rsp.msg;
                } else {
                    this.$store.commit("navbar", true);
                    this.$router.push("/");
                    this.$alert("info", "注册成功，请登录邮箱(" + this.email + ")激活账号。如未能收到邮件，请检查激活邮件是否被识别为垃圾邮件，其他问题请联系本站管理员。")
                }
            });
        }
    },
}
</script>

<style>
.fill-center {
    margin-top: 6%;
}
</style>

