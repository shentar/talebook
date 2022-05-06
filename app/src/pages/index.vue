<template>
    <div>
        <v-row>
            <v-col cols=12>
                <a class="ma-0 title" @click="fetch_books(true)" title="换一批" style="color:#000000">随机推荐
                    <v-icon>mdi-reload</v-icon>
                </a>
            </v-col>
            <v-col cols=12 class="new-legend">
                <v-divider/>
            </v-col>
            <v-col cols=4 xs=4 sm=4 md=2 lg=1 v-for="(book,idx) in get_random_books" :key="'rec'+idx+book.id">
                <v-card :to="book.href" class="ma-1">
                    <v-img :src="book.img" :title="book.title" :aspect-ratio="11/15"></v-img>
                </v-card>
            </v-col>
        </v-row>
        <v-row>
            <v-col cols=12>
                <a class="ma-0 title" @click="fetch_books(false)" title="换一批" style="color:#000000">新书推荐
                    <v-icon>mdi-reload</v-icon>
                </a>
            </v-col>
            <v-col cols=12 class="new-legend">
                <v-divider/>
            </v-col>
            <v-col cols=12 style="padding-top: 30px">
                <book-cards :books="get_recent_books"></book-cards>
            </v-col>
        </v-row>
        <v-row style="padding-top: 40px">
            <v-col cols=12 sm=6 md=4 v-for="nav in navs" :key="nav.text">
                <v-card outlined>
                    <v-list>
                        <v-list-item :to="nav.href">
                            <v-list-item-avatar large color='primary'>
                                <v-icon dark>{{ nav.icon }}</v-icon>
                            </v-list-item-avatar>
                            <v-list-item-content>
                                <v-list-item-title>{{ nav.text }}</v-list-item-title>
                                <v-list-item-subtitle>{{ nav.subtitle }}</v-list-item-subtitle>
                            </v-list-item-content>
                            <v-list-item-action>
                                <v-icon>mdi-arrow-right</v-icon>
                            </v-list-item-action>
                        </v-list-item>
                    </v-list>
                </v-card>
            </v-col>
        </v-row>
    </div>
</template>

<script>
import BookCards from "~/components/BookCards.vue";

export default {
    name: 'IndexPage',
    components: {
        BookCards,
    },
    computed: {
        get_random_books: function () {
            return this.random_books.map(b => {
                b['href'] = "/book/" + b.id;
                return b;
            });
        },
        get_recent_books: function () {
            return this.new_books.map(b => {
                b['href'] = "/book/" + b.id;
                return b;
            });
        },
    },
    created() {
        this.$store.commit('navbar', true);
        this.navs = [
            {icon: 'widgets', href: '/nav', text: '分类导览', count: this.$store.state.sys.books},
            {icon: 'mdi-human-greeting', href: '/author', text: '作者', count: this.$store.state.sys.authors},
            {icon: 'mdi-home-group', href: '/publisher', text: '出版社', count: this.$store.state.sys.publishers},
            {icon: 'mdi-tag-heart', href: '/tag', text: '标签', count: this.$store.state.sys.tags},
            {icon: 'mdi-history', href: '/recent', text: '所有书籍'},
            {icon: 'mdi-trending-up', href: '/hot', text: '热度榜单'},
        ]
    },
    async asyncData({app, res}) {
        if (res !== undefined) {
            res.setHeader('Cache-Control', 'no-cache');
        }
        return app.$backend("/index?random=12&recent=12");
    },
    data: () => ({
        random_books: [],
        new_books: [],
        navs: [],
    }),
    head: () => ({
        titleTemplate: "%s",
    }),
    methods: {
        fetch_books(isRandom) {
            let dst_uri = "/index?recent=12";
            if (isRandom) {
                dst_uri = "/index?random=12"
            }
            this.$backend(dst_uri).then((rsp) => {
                    if (isRandom) {
                        this.random_books = rsp.random_books
                    } else {
                        this.new_books = rsp.new_books
                    }
                }
            )
        }
    }

}
</script>

<style>
.new-legend {
    padding-top: 0;
    padding-bottom: 0;
    margin-top: 0;
    margin-bottom: 0;
}
</style>
