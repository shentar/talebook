<template>
    <v-row align="start">
        <v-col cols="12">
            <v-dialog v-model="can_push" persistent width="300">
                <v-card>
                    <v-card-title class="">推送到邮箱</v-card-title>
                    <v-card-text>
                        <p>填写接收书籍附件邮箱地址：</p>
                        <v-combobox
                            :items="email_items"
                            :rules="[check_email]"
                            outlined
                            dense
                            v-model="mail_to"
                            label="Email*"
                            auto-select-first
                            required
                        ></v-combobox>
                        <small>*如果目标邮箱需要识别发件人地址，请先将本站邮箱加入到白名单:<br/>{{
                                kindle_sender
                            }}</small>
                    </v-card-text>
                    <v-card-actions>
                        <v-btn color="" text @click="dialog_kindle = false">取消</v-btn>
                        <v-spacer></v-spacer>
                        <v-btn color="primary" text @click="sendto_kindle">发送</v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>

            <v-dialog v-model="can_download" persistent width="300">
                <v-card>
                    <v-card-title color="primary" class="">下载书籍</v-card-title>
                    <v-card-text>
                        <v-list v-if="book.files.length > 0">
                            <v-list-item :key="'file-'+file.format" v-for="file in book.files" target="_blank"
                                         :href="file.href">
                                <v-list-item-avatar color='primary'>
                                    <v-icon dark>get_app</v-icon>
                                </v-list-item-avatar>
                                <v-list-item-content>
                                    <v-list-item-title>{{ file.format }}</v-list-item-title>
                                    <v-list-item-subtitle v-if="file.size>=1048576">{{
                                            parseInt(file.size / 1048576)
                                        }}MB
                                    </v-list-item-subtitle>
                                    <v-list-item-subtitle v-else>{{
                                            parseInt(file.size / 1024)
                                        }}KB
                                    </v-list-item-subtitle>
                                </v-list-item-content>
                            </v-list-item>
                        </v-list>
                        <p v-else><br/>本书暂无可供下载的文件格式</p>
                    </v-card-text>
                    <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn text @click="dialog_download = false">关闭</v-btn>
                        <v-spacer></v-spacer>
                    </v-card-actions>
                </v-card>
            </v-dialog>

            <v-card v-if="dialog_refer">
                <v-toolbar flat dense dark color="primary">
                    从互联网同步书籍信息
                    <v-spacer></v-spacer>
                    <v-btn outlined text @click="dialog_refer = false">取消</v-btn>
                </v-toolbar>
                <v-card-text xclass="pt-3 px-3 px-sm-6">
                    <p class="py-6 text-center" v-if="refer_books_loading">
                        <v-progress-circular indeterminate color="primary"></v-progress-circular>
                    </p>
                    <p class="py-6 text-center" v-else-if="refer_books.length === 0">无匹配的书籍信息</p>
                    <template v-else>
                        <p style="margin-bottom: 16px">请选择最匹配的记录复制为本书的描述信息</p>
                        <book-cards :books="refer_books">
                            <template #actions="{ book }">
                                <v-card-actions>
                                    <v-chip class="mr-1" small v-if="book.author_sort">{{ book.author_sort }}</v-chip>
                                    <v-chip class="mr-1" small v-if="book.publisher">{{ book.publisher }}</v-chip>
                                    <v-chip small v-if="book.pubyear">{{ book.pubyear }}</v-chip>
                                </v-card-actions>
                                <v-divider></v-divider>
                                <v-card-actions>
                                    <v-chip
                                        small
                                        dark
                                        :href="book.website"
                                        target="__blank"
                                        :color="book.source === '豆瓣' ? 'green' : 'blue'">
                                        {{ book.source }}
                                    </v-chip>
                                    <v-spacer></v-spacer>
                                    <v-menu offset-y right>
                                        <template v-slot:activator="{ on }">
                                            <v-btn color="primary" small rounded v-on="on">
                                                <v-icon small>done</v-icon>
                                                设置
                                            </v-btn>
                                        </template>
                                        <v-list dense>
                                            <v-list-item @click="set_refer(book.provider_key, book.provider_value)">
                                                <v-list-item-title>设置书籍信息及图片</v-list-item-title>
                                            </v-list-item>
                                            <v-list-item
                                                @click="set_refer(book.provider_key, book.provider_value, { only_meta: 'yes' })">
                                                <v-list-item-title>仅设置书籍信息</v-list-item-title>
                                            </v-list-item>
                                            <v-list-item
                                                @click="set_refer(book.provider_key, book.provider_value, { only_cover: 'yes' })">
                                                <v-list-item-title>仅设置书籍图片</v-list-item-title>
                                            </v-list-item>
                                        </v-list>
                                    </v-menu>
                                </v-card-actions>
                            </template>
                        </book-cards>
                    </template>
                </v-card-text>
            </v-card>

            <v-card v-if="!dialog_refer">
                <v-toolbar flat dense color="white" v-if="this.err === 'ok'">
                    <!-- download -->
                    <v-btn icon small fab @click="dialog_download = true" title="下载书籍">
                        <v-icon>get_app</v-icon>
                    </v-btn>

                    <v-btn v-if="book.fav === true" icon small fab width="70px" title="点击取消收藏" @click="fav_book">
                        <v-icon style="color: #BA476B">mdi-heart-plus</v-icon>
                        <span style="color: #BA476B"> &nbsp;取消</span>
                    </v-btn>
                    <v-btn v-else icon small fab width="70px" @click="fav_book">
                        <v-icon title="点击收藏">mdi-heart-plus-outline</v-icon>
                        <span> &nbsp;收藏</span>
                    </v-btn>

                    <v-spacer></v-spacer>

                    <v-btn :small="tiny" dark color="primary" class="mx-2 d-flex d-sm-flex"
                           @click="dialog_kindle = !dialog_kindle">
                        <v-icon left v-if="!tiny">email</v-icon>
                        推送
                    </v-btn>
                    <v-btn :small="tiny" dark color="primary" class="mx-2 d-flex d-sm-flex" @click="online_read">
                        <v-icon left v-if="!tiny">import_contacts</v-icon>
                        阅读
                    </v-btn>

                    <template v-if="book.is_owner">
                        <v-menu offset-y>
                            <template v-slot:activator="{ on }">
                                <v-btn v-on="on" dark color="primary" class="ml-2" :small="tiny">管理
                                    <v-icon small>more_vert</v-icon>
                                </v-btn>
                            </template>
                            <v-list>
                                <v-list-item :to="'/book/' + book.id + '/edit'">
                                    <v-icon>settings_applications</v-icon>
                                    编辑书籍信息
                                </v-list-item>
                                <v-list-item @click="get_refer">
                                    <v-icon>apps</v-icon>
                                    从互联网更新信息
                                </v-list-item>
                                <v-divider></v-divider>
                                <v-list-item @click="delete_book">
                                    <v-icon>delete_forever</v-icon>
                                    删除此书
                                </v-list-item>
                            </v-list>
                        </v-menu>
                    </template>
                </v-toolbar>
                <v-row v-if="this.err !== 'ok'">
                    <v-card-text class='text-center'>
                        <div>
                            <span color="red">{{ this.msg }}</span> <br/><br/><br/>
                            <v-btn color="primary" @click="$router.push('/')">返回主页
                            </v-btn>
                            <br/><br/><br/>
                        </div>
                    </v-card-text>
                </v-row>
                <v-row v-else>
                    <v-col class="ma-auto" cols="8" sm="4">
                        <v-img :src="book.img" :aspect-ratio="11/15" max-height="500px" class="book-img"
                               contain></v-img>
                    </v-col>
                    <v-col cols="12" sm="8">
                        <v-card-text>
                            <div>
                                <p class='title mb-0'>{{ book.title }}</p>
                                <span color="grey--text">{{ book.author }}著，{{ pub_year }}年版</span>
                                <span
                                    v-if='book.files.length>0 && book.files[0].format==="PDF" && book.files[0].size >= 1048576'
                                    color="grey--text" style="font-weight: bold">&nbsp;[文件格式: PDF - {{
                                        parseInt(book.files[0].size / 1048576)
                                    }}MB]
                                </span>
                                <span
                                    v-else-if='book.files.length>0 && book.files[0].format==="PDF" && book.files[0].size < 1048576'
                                    color="grey--text" style="font-weight: bold">&nbsp;[文件格式: PDF - {{
                                        parseInt(book.files[0].size / 1024)
                                    }}KB]
                                </span>
                            </div>
                            <v-rating v-model="book.rating" color="yellow accent-4" length="10" readonly dense
                                      small></v-rating>
                            <br/>
                            <div class="tag-chips">
                                <template v-for="author in book.authors">
                                    <v-chip
                                        rounded
                                        small
                                        dark
                                        color="indigo"
                                        :to="'/author/' + encodeURIComponent(author)"
                                        :key="'author-' + author">
                                        <v-icon>face</v-icon>
                                        {{ author }}
                                    </v-chip>
                                </template>
                                <v-chip rounded small dark color="indigo"
                                        :to="'/publisher/' + encodeURIComponent(book.publisher)">
                                    <v-icon>group</v-icon>
                                    出版：{{ book.publisher }}
                                </v-chip>
                                <v-chip
                                    rounded
                                    small
                                    dark
                                    color="indigo"
                                    v-if="book.series"
                                    :to="'/series/' + encodeURIComponent(book.series)">
                                    <v-icon>explore</v-icon>
                                    丛书: {{ book.series }}
                                </v-chip>
                                <v-chip rounded small dark color="grey" v-if="book.isbn">
                                    <v-icon>explore</v-icon>
                                    ISBN：{{ book.isbn }}
                                </v-chip>
                                <template v-for="tag in book.tags">
                                    <v-chip
                                        rounded
                                        small
                                        dark
                                        color="grey"
                                        :key="'tag-' + tag"
                                        v-if="tag"
                                        :to="'/tag/' + encodeURIComponent(tag)">
                                        <v-icon>loyalty</v-icon>
                                        {{ tag }}
                                    </v-chip>
                                </template>
                                <v-chip v-if="db_link !== undefined"
                                        rounded
                                        small
                                        dark
                                        color="green"
                                        :href="db_link"
                                        target="__blank">
                                    <v-icon>explore</v-icon>
                                    豆瓣链接
                                </v-chip>
                            </div>
                        </v-card-text>
                        <v-card-text v-if="this.err === 'ok'">
                            <p v-if="book.comments" v-html="book.comments"></p>
                            <p v-else>点击浏览详情</p>
                        </v-card-text>
                    </v-col>
                </v-row>
                <v-card-text class="align-right book-footer" v-if="this.err === 'ok'">
                    <span class="grey--text"> {{ book.collector }} @ {{
                            book.timestamp
                        }} | [热度指数 {{ get_hot_score }}]</span>
                </v-card-text>
            </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4">
            <v-card outlined v-if="this.err === 'ok'">
                <v-list>
                    <v-list-item @click="online_read">
                        <v-list-item-avatar large color="primary">
                            <v-icon dark>import_contacts</v-icon>
                        </v-list-item-avatar>
                        <v-list-item-content>
                            <v-list-item-title>在线阅读</v-list-item-title>
                        </v-list-item-content>
                        <v-list-item-action>
                            <v-icon>mdi-arrow-right</v-icon>
                        </v-list-item-action>
                    </v-list-item>
                </v-list>
            </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4">
            <v-card outlined v-if="this.err === 'ok'">
                <v-list>
                    <v-list-item @click="dialog_download = true">
                        <v-list-item-avatar large color="primary">
                            <v-icon dark>get_app</v-icon>
                        </v-list-item-avatar>
                        <v-list-item-content>
                            <v-list-item-title>下载</v-list-item-title>
                        </v-list-item-content>
                        <v-list-item-action>
                            <v-icon>mdi-arrow-right</v-icon>
                        </v-list-item-action>
                    </v-list-item>
                </v-list>
            </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4">
            <v-card outlined v-if="this.err === 'ok'">
                <v-list>
                    <v-list-item @click="dialog_kindle = !dialog_kindle">
                        <v-list-item-avatar large color="primary">
                            <v-icon dark>email</v-icon>
                        </v-list-item-avatar>
                        <v-list-item-content>
                            <v-list-item-title>推送至Email</v-list-item-title>
                        </v-list-item-content>
                        <v-list-item-action>
                            <v-icon>mdi-arrow-right</v-icon>
                        </v-list-item-action>
                    </v-list-item>
                </v-list>
            </v-card>
        </v-col>
    </v-row>
</template>

<script>
import BookCards from "~/components/BookCards.vue";

export default {
    components: {
        BookCards,
    },
    computed: {
        pub_year: function () {
            if (this.book === null || this.book.pubdate == null) {
                return "N/A";
            }
            return this.book.pubdate.split("-")[0];
        },
        tiny: function () {
            return this.$vuetify.breakpoint.xsOnly;
        },
        email_items: function () {
            var emails = [this.$store.state.user.kindle_email];
            if (process.client) {
                emails.push(this.$cookies.get("last_mailto"));
            }
            return emails.filter((value, index, self) => {
                return value !== "" && value !== undefined && value !== null && self.indexOf(value) === index;
            });
        },
        db_link: function () {
            if (this.dbid !== undefined && this.dbid !== "") {
                return "https://book.douban.com/subject/" + this.dbid;
            } else {
                return undefined;
            }
        },
        get_hot_score: function () {
            return this.book.count_download + this.book.count_visit * 2
        },
        can_download: function () {
            if (!this.dialog_download) {
                return false;
            }

            const user = this.$store.state.user;
            const sysinfo = this.$store.state.sys;
            if (user.is_login) {
                if (!user.is_active) {
                    this.$alert("info", "未激活用户禁止下载书籍，请登录注册邮箱激活账号。", "/user/detail");
                    return false
                }
                if (user.pems.indexOf("S") > -1) {
                    this.$alert("info", "当前用户禁止下载书籍，请联系管理员申请权限。", "/user/detail");
                    this.dialog_download = false;
                    return false;
                } else {
                    return true;
                }
            }

            if (!sysinfo.allow.download) {
                this.$alert("info", "禁止游客下载书籍，请登录或者注册账号。", "/login?from=/book/" + this.book.id);
                this.dialog_download = false;
                return false;
            }

            return true;
        },
        can_push: function () {
            if (!this.dialog_kindle) {
                return false;
            }

            const user = this.$store.state.user;
            const sysinfo = this.$store.state.sys;
            if (user.is_login) {
                if (!user.is_active) {
                    this.$alert("info", "未激活用户禁止推送书籍，请登录注册邮箱激活账号。", "/user/detail");
                    return false;
                }
                if (user.pems.indexOf("P") > -1) {
                    this.$alert("info", "当前用户禁止推送书籍，请联系管理员申请权限。", "/user/detail");
                    this.dialog_kindle = false
                    return false;
                } else {
                    return true;
                }
            }

            if (!sysinfo.allow.push) {
                this.$alert("info", "禁止游客推送书籍，请登录或者注册账号。", "/login?from=/book/" + this.book.id);
                this.dialog_kindle = false;
                return false;
            }

            return true
        }
    },
    data: () => ({
        err: "",
        msg: "",
        book: {id: 0, title: "", files: [], tags: [], pubdate: "", count_download: 0, count_visit: 0, fav: false},
        dbid: "",
        debug: false,
        mail_to: "",
        kindle_sender: "",
        dialog_download: false,
        dialog_kindle: false,
        dialog_refer: false,
        dialog_msg: false,
        refer_books_loading: false,
        refer_books: [],
        email_rules: function (email) {
            var re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
            return (email !== this.kindle_sender && re.test(email)) || "Invalid email format";
        },
    }),
    async asyncData({params, app, res}) {
        if (res !== undefined) {
            res.setHeader("Cache-Control", "no-cache");
        }
        return app.$backend(`/book/${params.bookid}`);
    },
    head() {
        return {
            title: this.book.title,
        };
    },
    created() {
        this.init(this.$route);
        this.mail_to = this.$store.state.user.kindle_email;
        if (process.client) {
            this.mail_to = this.$cookies.get("last_mailto");
        }
    },
    beforeRouteUpdate(to, from, next) {
        this.init(to, next);
    },
    methods: {
        init(route, next) {
            this.$store.commit("navbar", true);
            if (next) next();
        },
        sendto_kindle() {
            if (process.client) {
                this.$cookies.set("last_mailto", this.mail_to);
            }
            this.$backend("/book/" + this.book.id + "/push", {
                method: "POST",
                body: "mail_to=" + this.mail_to,
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            }).then((rsp) => {
                this.dialog_kindle = false;
                if (rsp.err === "ok") {
                    this.$alert("success", rsp.msg, "#");
                } else {
                    this.$alert("error", rsp.msg, rsp.to);
                }
            });
        },
        can_read: function () {
            const user = this.$store.state.user;
            const sysinfo = this.$store.state.sys;
            if (user.is_login) {
                if (!user.is_active) {
                    this.$alert("info", "未激活用户禁止在线阅读书籍，请登录注册邮箱激活账号。", "/user/detail");
                    return false;
                }
                if (user.pems.indexOf("R") > -1) {
                    this.$alert("info", "当前用户禁止在线阅读书籍，请联系管理员申请权限。", "/user/detail");
                    return false;
                } else {
                    return true;
                }
            }

            if (!sysinfo.allow.read) {
                this.$alert("info", "禁止游客在线阅读书籍，请登录或者注册账号。", "/login?from=/book/" + this.book.id);
                return false;
            }

            return true;
        },
        online_read() {
            if (!this.can_read()) {
                return
            }

            const userAgent = window.navigator.userAgent.toLowerCase();
            if (userAgent.indexOf("micromessenger") === -1) {
                window.open("/read/" + this.book.id, "_blank");
            } else {
                this.$alert("error", "微信无法加载阅读器，请在浏览器中打开后阅读：<br/><br/>1. 点击右上角；<br/>2. 选择“在浏览器打开”。");
            }
        },
        get_refer() {
            this.dialog_refer = true;
            this.refer_books_loading = true;
            this.$backend("/book/" + this.book.id + "/refer")
                .then((rsp) => {
                    this.refer_books = rsp.books.map((b) => {
                        b.href = "";
                        b.img = "/get/pcover?url=" + encodeURIComponent(b.cover_url);
                        return b;
                    });
                })
                .finally(() => {
                    this.refer_books_loading = false;
                });
        },
        set_refer(provider_key, provider_value, opt) {
            var data = new URLSearchParams(opt);
            data.append("provider_key", provider_key);
            data.append("provider_value", provider_value);
            this.$backend("/book/" + this.book.id + "/refer", {
                method: "POST",
                body: data,
            }).then((rsp) => {
                this.dialog_refer = false;
                if (rsp.err === "ok") {
                    this.$router.push("/book/" + this.book.id);
                    location.reload();
                    this.$alert("success", "设置成功！");
                } else {
                    this.$alert("error", rsp.msg);
                }
                this.init(this.$route);
            });
        },
        delete_book() {
            const user = this.$store.state.user
            if (user.pems.indexOf("D") > -1) {
                this.$alert("info", "当前用户禁止删除书籍，请联系管理员。", "/user/detail");
                return
            }
            this.$backend("/book/" + this.book.id + "/delete", {
                method: "POST",
            }).then((rsp) => {
                if (rsp.err === "ok") {
                    this.$alert("success", "删除成功");
                    this.$router.push("/");
                } else {
                    this.$alert("error", rsp.msg);
                }
            });
        },
        check_email(email) {
            if (email === this.kindle_sender) {
                return "发件邮件不可作为收件人";
            }
            var re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
            return re.test(email) || "Email格式错误";
        },
        fav_book() {
            const user = this.$store.state.user
            if (!user.is_login) {
                this.$alert("info", "请先登录后再收藏书籍！", "/login/?from=/book/" + this.book.id);
                return
            }

            if (!user.is_active) {
                this.$alert("info", "请先激活用户后再收藏书籍！", "/user/detail");
                return
            }

            this.$backend("/book/" + this.book.id + "/fav", {
                method: this.book.fav ? "DELETE" : "POST",
            }).then((rsp) => {
                if (rsp.err === "ok") {
                    this.book.fav = !this.book.fav
                    this.$alert("success", rsp.msg);
                } else {
                    this.$alert("error", rsp.msg, rsp.to);
                }
            });
        },
    },
};
</script>

<style>
.book-img {
    border-radius: 4px;
}

.align-right {
    text-align: right;
}

.book-footer {
    padding-top: 0;
    padding-bottom: 3px;
}

.tag-chips a {
    margin: 4px 2px;
}

.book-comments {
    /*text-indent: 2em;*/
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    text-overflow: clip;
    margin-top: 6px;
    text-align: left;
}

.book-comments p {
    font-size: small;
    margin-bottom: 0;
}

h1.book-detail-title {
    line-height: inherit;
}

</style>