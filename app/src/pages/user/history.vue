<template>
    <div>
        <v-row align=start v-if="history.length === 0">
            <v-col cols=12 xs=6>
                <p class="title"> 暂无阅读历史。请尽情<a href="/">畅游书籍的海洋</a>吧~ </p>
            </v-col>
        </v-row>
        <v-row v-else v-for="item in history" :key="item.name">
            <v-col cols=12 xs=6>
                <legend>{{ item.name }}</legend>
                <v-divider></v-divider>
            </v-col>
            <v-col cols=12 xs=6 v-if="item.books.length === 0">
                <p class="pb-6">无记录</p>
            </v-col>
            <v-col cols=4 xs=4 sm=4 md=2 lg=1 v-else v-for="book in item.books" :key="item.name + book.id">
                <v-card class="ma-1">
                    <a :href="'/book/' + book.id" target="_blank">
                        <v-img :src="get_book_img(book)" :title="book.title" :aspect-ratio="11/15"
                               class="his-img"></v-img>
                    </a>
                </v-card>
            </v-col>
        </v-row>
    </div>
</template>

<script>
export default {
    components: {},
    computed: {
        history: function () {
            if (this.user.extra === undefined) {
                return []
            }
            return [
                {name: '我的上传', books: this.get_history(this.user.extra.upload_history)},
                {name: '在线阅读', books: this.get_history(this.user.extra.read_history)},
                {name: '下载记录', books: this.get_history(this.user.extra.download_history)},
                {name: '推送记录', books: this.get_history(this.user.extra.push_history)},
                {name: '浏览记录', books: this.get_history(this.user.extra.visit_history)},
            ]
        },
        get_book_img() {
            return function (book) {
                let uri = "/get/cover/" + book.id + ".jpg"
                if (book.lm !== undefined) {
                    uri += "?t=" + book.lm
                }
                if (this.user.cdn !== undefined) {
                    return this.user.cdn + uri
                } else {
                    return uri
                }
            }
        }
    },
    data: () => ({
        user: {},
    }),
    async asyncData({params, app, res}) {
        if (res !== undefined) {
            res.setHeader('Cache-Control', 'no-cache');
        }
        return app.$backend("/user/info?detail=1");
    },
    head: () => ({
        title: "近期访问记录",
    }),
    created() {
        this.init(this.$route);
    },
    beforeRouteUpdate(to, from, next) {
        this.init(to, next);
    },
    methods: {
        init(route, next) {
            this.$store.commit('navbar', true);
            this.$backend("/user/info?detail=1")
                .then(rsp => {
                    this.user = rsp.user;
                });
            if (next) next();
        },
        get_history(his) {
            if (!his) {
                return [];
            }
            return his.map(b => {
                b.href = '/book/' + b.id;
                return b;
            });
        },
    },
}
</script>

<style>
.his-img {
    border-radius: 4px;
}
</style>
