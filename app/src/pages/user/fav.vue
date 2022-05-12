<template>
    <div>
        <v-row align=start v-if="fav_books.length === 0">
            <v-col cols=12 xs=6>
                <p class="title">暂未收藏任何书籍。</p>
            </v-col>
        </v-row>
        <v-row v-else>
            <v-col cols=12 xs=6>
                <legend>我的搜藏</legend>
                <v-divider></v-divider>
            </v-col>
            <v-col cols=4 xs=4 sm=4 md=2 lg=1 v-for="(book,idx) in fav_books" :key="idx+'-fav-books-'+book.id">
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
        fav_books: function () {
            if (this.user.extra === undefined) {
                return []
            }
            return this.user.extra.fav_history
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
    created() {
        this.init(this.$route);
    },
    beforeRouteUpdate(to, from, next) {
        this.init(to, next);
    },
    head: () => ({
        title: "我的收藏",
    }),
    methods: {
        init(route, next) {
            this.$store.commit('navbar', true);
            this.$backend("/user/info?detail=1")
                .then(rsp => {
                    this.user = rsp.user;
                });
            if (next) next();
        },
    },
}

</script>