<template>
    <div>
        <v-btn bottom color="pink" dark fab fixed right @click="dialog = !dialog">
            <v-icon>mdi-upload</v-icon>
        </v-btn>
        <v-dialog v-model="can_upload" persistent transition="dialog-bottom-transition" width="300">
            <v-card>
                <v-toolbar flat dense dark color="primary">
                    上传书籍
                    <v-spacer></v-spacer>
                    <v-btn color="" text @click="dialog = false">关闭</v-btn>
                </v-toolbar>
                <v-card-title></v-card-title>
                <v-card-text>
                    <p>受限于服务器能力，请勿上传100M的大文件书籍。</p>
                    <v-form ref="form" @submit="do_upload">
                        <v-file-input v-model="ebooks" label="请选择要上传的电子书"></v-file-input>
                    </v-form>
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn :loading="loading" color="primary" @click="do_upload">上传</v-btn>
                    <v-spacer></v-spacer>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script>
export default {
    data: () => ({
        loading: false,
        dialog: false,
        ebooks: null,
    }),
    methods: {
        do_upload: function () {
            this.loading = true;
            var data = new FormData();
            data.append("ebook", this.ebooks);
            this.$backend("/book/upload", {
                method: 'POST',
                body: data,
            })
                .then(rsp => {
                    this.dialog = false;
                    if (rsp.err === 'ok') {
                        this.$alert("success", "上传成功！", "/book/" + rsp.book_id);
                        this.$router.push("/book/" + rsp.book_id)
                    } else if (rsp.err === 'samebook') {
                        this.$alert("error", rsp.msg, "/book/" + rsp.book_id);
                        this.$router.push("/book/" + rsp.book_id)
                    } else {
                        this.$alert("error", rsp.msg, rsp.to);
                    }
                })
                .finally(() => {
                    this.loading = false;
                });
        },
    },
    computed: {
        can_upload: function () {
            if (!this.dialog) {
                return false
            }

            const user = this.$store.state.user;
            if (!user.is_login) {
                this.dialog = false
                this.$alert("info", "请登录后操作。")
                return false
            }

            if (!user.is_active) {
                this.dialog = false
                this.$alert("info", "请激活账号后操作。")
                return false
            }

            if (user.pems === undefined) {
                this.dialog = false
                this.$alert("info", "没有权限上传书籍，请联系管理员申请。")
                return false
            }

            // 未禁止即可以上传。
            if (user.pems.indexOf("U") > -1) {
                this.dialog = false
                this.$alert("info", "没有权限上传书籍，请联系管理员申请。")
                return false
            }

            return true
        },
    },
}
</script>

