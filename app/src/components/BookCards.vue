<template>
    <v-row>
        <v-col cols=12 xs=12 sm=6 md=4 lg=3 v-for="(book,idx) in render_books" :key="idx+'-books-'+book.id"
               class="book-list-card">
            <v-card :href="book.href" target="_blank">
                <v-row>
                    <v-col cols=4 class='col-book-img'>
                        <v-img :src="book.img" :title="book.title" :aspect-ratio="11/15"></v-img>
                    </v-col>
                    <v-col cols=8 class='col-book-info'>
                        <v-card-text class="pb-0" align-left>
                            <div class="book-title">{{ book.title }}</div>
                            <slot name="introduce" :book="book"></slot>
                            <div class="book-comments">
                                <p v-if="book.comments" v-html="book.comments"></p>
                                <p v-else>点击浏览详情</p>
                            </div>
                        </v-card-text>
                    </v-col>
                </v-row>
                <slot name="actions" :book="book"></slot>
            </v-card>
        </v-col>
    </v-row>
</template>

<script>
export default {
    props: {
        books: Array,
    },
    components: {},
    computed: {
        render_books: function () {
            return this.books.map(b => {
                if (b['href'] === undefined) {
                    b['href'] = "/book/" + b.id;
                }
                return b;
            });
        },
    },
    data: () => {
        return {}
    },
}
</script>

<style scoped>
.book-title {
    display: block;
    /*height: 1em;*/
    overflow-y: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    text-overflow: clip;
    text-align: left;
    font-weight: bold;
}

.book-comments {
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 5;
    -webkit-box-orient: vertical;
    text-overflow: clip;
    margin-top: 6px;
    text-align: left;
}

.book-comments p {
    font-size: small;
    margin-bottom: 0;
}

.book-list-card .row {
    margin-bottom: 0;
}

.page-title {
    font-weight: bold;
    text-align: left;
}

.new-legend {
    margin-top: 30px;
    margin-bottom: 20px;
}

.col-book-img {
    padding: 0 0 0 12px;
}

.col-book-info {
    padding: 0;
    margin-left: -6px;
    margin-top: -6px;
}

</style>
