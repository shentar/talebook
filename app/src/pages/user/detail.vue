<template>
    <v-form ref="form" @submit.prevent="save">
        <v-row align=start>
            <v-col cols=3>
                <v-subheader class="pa-0 float-right">头像</v-subheader>
            </v-col>
            <v-col cols=9>
                <v-img class="float-left" height=80 contain :src="user.avatar"></v-img>
                <v-subheader class="">
                    <a href="https://cn.gravatar.com" target="_blank">点击修改</a>
                </v-subheader>
            </v-col>

            <v-col cols=3>
                <v-subheader class="pa-0 float-right">用户名</v-subheader>
            </v-col>
            <v-col cols=9><p class="pt-3 mb-0">{{ user.username }}</p></v-col>

            <v-col cols=3>
                <v-subheader class="pa-0 float-right">邮箱</v-subheader>
            </v-col>
            <v-col cols=9><p class="pt-3 mb-0">{{ user.email }}<a href='#' v-if="!user.is_active"
                                                                  @click='send_active_email'>重新发送激活邮件</a></p></v-col>

            <v-col cols=3>
                <v-subheader class="pa-0 float-right">密码</v-subheader>
            </v-col>
            <v-col cols=9>
                <v-subheader class="pa-0">
                    <a href="#" @click.stop="show_pass = ! show_pass">点击修改</a>
                </v-subheader>
                <div v-if="show_pass">
                    <v-text-field solo v-model="user.password0" label="当前密码" type="password"
                                  autocomplete="new-password0" :rules="[rules.pass]"></v-text-field>
                    <v-text-field solo v-model="user.password1" label="新密码" type="password" autocomplete="new-password1"
                                  :rules="[rules.pass]"></v-text-field>
                    <v-text-field solo v-model="user.password2" label="确认密码" type="password"
                                  autocomplete="new-password2" :rules="[valid]"></v-text-field>
                </div>
            </v-col>

            <v-col cols=3>
                <v-subheader class="pa-0 float-right">昵称</v-subheader>
            </v-col>
            <v-col cols=9>
                <v-text-field solo v-model="user.nickname" label="昵称" type="text" autocomplete="new-nickname"
                              :rules="[rules.nick]"></v-text-field>
            </v-col>

            <v-col cols=3>
                <v-subheader class="pa-0 float-right">权限</v-subheader>
            </v-col>
            <v-col cols=9>
                <p v-if="gen_perms(user.pems, true) !== ''" class="pt-3 mb-0">
                    <v-icon style="color: green;">mdi-check-circle-outline</v-icon>
                    {{ gen_perms(user.pems, true) }}
                </p>
                <p v-if="gen_perms(user.pems, false) !== ''" class="pt-3 mb-0">
                    <v-icon style="color: red;">mdi-close-circle-outline</v-icon>
                    {{ gen_perms(user.pems, false) }}
                </p>
                <br/>
                <p style="font-style: italic;font-size: smaller;color: gray;">
                    * 1.在线阅读权限仅限非PDF类书籍，PDF书籍需要下载权限；2.编辑和删除权限仅限自己上传的书籍；3.未激活用户仅支持浏览导航页。
                </p>
            </v-col>

            <v-col cols=3>
                <v-subheader class="pa-0 float-right">Kindle地址</v-subheader>
            </v-col>
            <v-col cols=9>
                <v-text-field solo v-model="user.kindle_email" label="Kindle" type="text" autocomplete="new-email"
                              :rules="[rules.email]"></v-text-field>
            </v-col>
            <v-col cols=12>
                <div class="text-center">
                    <v-btn dark large rounded color="orange" @click="save">保存</v-btn>
                </div>
            </v-col>
        </v-row>
    </v-form>
</template>

<script>
export default {
    data: () => ({
        user: {},
        show_pass: false,
        rules: {
            pass: v => v === undefined || v.length === 0 || v.length >= 8 || 'Min 8 characters',
            nick: v => v === undefined || v.length === 0 || v.length >= 2 || 'Min 2 characters',
            email: function (email) {
                var re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
                return email === undefined || email.length === 0 || re.test(email) || "Invalid email format";
            },
        },
        permissions: {
            "r": "在线阅读*",
            "s": "下载*",
            "p": "推送",
            "e": "编辑*",
            "d": "删除*",
            "u": "上传"
        },
    }),
    async asyncData({params, app, res}) {
        if (res !== undefined) {
            res.setHeader('Cache-Control', 'no-cache');
        }
        return app.$backend("/user/info?detail=1");
    },
    head: () => ({
        title: "用户中心",
    }),
    created() {
        this.init(this.$route);
    },
    beforeRouteUpdate(to, from, next) {
        this.init(to, next);
    },
    computed: {
        gen_perms() {
            return function (perms, allow) {
                if (perms === undefined) {
                    perms = "usedpr"
                }

                if (this.user.is_active === undefined || this.user.is_active === false) {
                    if (allow) {
                        return ""
                    } else {
                        return "未激活*"
                    }
                }

                let pstr = ""
                for (let i of Object.keys(this.permissions)) {
                    if (perms.indexOf(i.toUpperCase()) > -1) {
                        if (!allow) {
                            pstr += (this.permissions[i] + " | ")
                        }
                    } else {
                        if (allow) {
                            pstr += (this.permissions[i] + " | ")
                        }
                    }
                }

                if (pstr.endsWith(" | ")) {
                    pstr = pstr.substring(0, pstr.length - 3)
                }
                return pstr
            }
        }
    },
    methods: {
        valid: function (v) {
            return v === this.user.password1 || "Password are not same."
        },
        save: function () {
            if (!this.$refs.form.validate()) {
                return false;
            }
            var d = {
                'password0': this.user.password0,
                'password1': this.user.password1,
                'password2': this.user.password2,
                'nickname': this.user.nickname,
                'kindle_email': this.user.kindle_email,
            }
            this.$backend('/user/update', {
                method: 'POST',
                body: JSON.stringify(d),
            }).then(rsp => {
                if (rsp.err !== 'ok') {
                    this.failmsg = rsp.msg;
                } else {
                    this.$alert("success", "修改成功！")
                }
            });
        },
        send_active_email: function () {
            this.$backend('/user/active/send').then(rsp => {
                if (rsp.err === 'ok') {
                    this.$alert("success", "激活邮件已发出！");
                } else {
                    this.$alert("danger", rsp.msg);
                }
            });
        },
        init(route, next) {
            this.$store.commit('navbar', true);
            this.$backend("/user/info?detail=1")
                .then(rsp => {
                    rsp.user.password0 = "";
                    rsp.user.password1 = "";
                    rsp.user.password2 = "";
                    this.user = rsp.user;
                });
            if (next) next();
        },
    },
}
</script>

