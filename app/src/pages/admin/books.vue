<template>
    <v-card>
        <v-card-title> 图书管理
            <v-chip small class="primary">Beta</v-chip>
        </v-card-title>
        <v-card-text> 此表格仅展示图书的部分字段，点击即可快捷修改。完整图书信息请点击链接查看书籍详情页面</v-card-text>
        <v-card-actions>
            <v-btn :disabled="loading" outlined color="primary" @click="getDataFromApi">
                <v-icon>mdi-reload</v-icon>
                刷新
            </v-btn>
            <v-spacer width="20px"></v-spacer>
            <v-checkbox :disabled="loading" v-model="getdup" :label="`获取重复书籍`">
            </v-checkbox>

            <template v-if="books_selected.length > 0">
                <v-spacer width="20px"></v-spacer>
                <v-btn :disabled="loading" outlined color="info" @click="auto_batch_op(true, false, false)">
                    <v-icon>mdi-delete</v-icon>
                    自动填充空缺字段
                </v-btn>

                <v-btn :disabled="loading" outlined color="info" @click="show_batch_tags=true">
                    <v-icon>loyalty</v-icon>
                    批量添加标签
                </v-btn>
                <v-btn :disabled="loading" outlined color="info" @click="show_batch_tags=true">
                    <v-icon>loyalty</v-icon>
                    批量删除标签
                </v-btn>
                <v-edit-dialog large :return-value.sync="batch_op_tags"
                               @save="auto_batch_op(false, batch_add_tags, batch_delete_tags)"
                               save-text="执行"
                               @cancel="show_batch_tags=false"
                               cancel-text="取消">
                    <template v-slot:input>
                        <!-- TAGS -->
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-combobox
                            v-model="batch_op_tags"
                            :items="batch_op_tags"
                            label="标签列表"
                            :search-input.sync="batch_op_tags"
                            hide-selected
                            multiple
                            small-chips>
                            <template v-slot:no-data>
                                <v-list-item>
                                    <span v-if="!batch_op_tags">请输入标签名称</span>
                                    <div v-else>
                                        <span class="subheading">添加标签</span>
                                        <v-chip color="green lighten-3" label small rounded> {{ batch_op_tags }}
                                        </v-chip>
                                    </div>
                                </v-list-item>
                            </template>
                            <!-- tag chip & close -->
                            <template v-slot:selection="{ attrs, item, parent, selected }">
                                <v-chip v-bind="attrs" color="green lighten-3" :input-value="selected" label small>
                                    <span class="pr-2"> {{ item }} </span>
                                    <v-icon small @click="parent.selectItem(item)">close</v-icon>
                                </v-chip>
                            </template>
                        </v-combobox>
                    </template>
                </v-edit-dialog>
            </template>
            <v-spacer></v-spacer>
            <v-text-field cols="2" dense v-model="search" append-icon="mdi-magnify" label="搜索"
                          @keydown.enter.prevent="getDataFromApi" single-line
                          hide-details></v-text-field>
        </v-card-actions>
        <v-data-table
            dense
            class="elevation-1 text-body-2"
            show-select
            v-model="books_selected"
            item-key="id"
            :search="search"
            :headers="headers"
            :items="items"
            :options.sync="options"
            :server-items-length="total"
            :loading="loading"
            :items-per-page="100"
            :footer-props="{ 'items-per-page-options': [10, 50, 100] }">
            <template v-slot:item.status="{ item }">
                <v-chip small v-if="item.status === 'ready'" class="success">可导入</v-chip>
                <v-chip small v-else-if="item.status === 'exist'" class="lighten-4">已存在</v-chip>
                <v-chip small v-else-if="item.status === 'imported'" class="primary">导入成功</v-chip>
                <v-chip small v-else-if="item.status === 'new'" class="grey">待扫描</v-chip>
                <v-chip small v-else class="info">{{ item.status }}</v-chip>
            </template>
            <template v-slot:item.id="{ item }">
                <a target="_blank" :href="`/book/${item.id}`">
                    <v-img :src="item.thumb" class="my-1" max-height="80" :aspect-ratio="3/4"/>
                </a>
            </template>
            <template v-slot:item.title="{ item }">
                <v-edit-dialog large :return-value.sync="item.title" @save="save(item, 'title')" save-text="保存"
                               cancel-text="取消">
                    <span class="three-lines" style="max-width: 200px">{{ item.title }}</span>

                    <template v-slot:input>
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-textarea v-model="item.title" label="书名" style="min-width: 400px" counter></v-textarea>
                    </template>
                </v-edit-dialog>
            </template>
            <template v-slot:item.isbn="{ item }">
                <v-edit-dialog large :return-value.sync="item.isbn" @save="save(item, 'isbn')" save-text="保存"
                               cancel-text="取消">
                    {{ item.isbn }}
                    <template v-slot:input>
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-text-field v-model="item.isbn" label="ISBN" counter></v-text-field>
                    </template>
                </v-edit-dialog>
            </template>
            <template v-slot:item.author="{ item }">
                <v-edit-dialog large :return-value.sync="item.author" @save="save(item, 'authors')" save-text="保存"
                               cancel-text="取消">
                    <span class="three-lines" style="max-width: 200px" v-if="item.authors">{{
                            item.authors.join("/")
                        }}</span>
                    <span v-else> - </span>
                    <template v-slot:input>
                        <!-- AUTHORS -->
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-combobox
                            v-model="item.authors"
                            :items="item.authors"
                            label="作者"
                            :search-input.sync="tag_input"
                            hide-selected
                            multiple
                            small-chips>
                            <template v-slot:no-data>
                                <v-list-item>
                                    <span v-if="!tag_input">请输入新的名称</span>
                                    <div v-else>
                                        <span class="subheading">添加</span>
                                        <v-chip color="green lighten-3" label small rounded> {{ tag_input }}</v-chip>
                                    </div>
                                </v-list-item>
                            </template>
                            <!-- tag chip & close -->
                            <template v-slot:selection="{ attrs, item, parent, selected }">
                                <v-chip v-bind="attrs" color="green lighten-3" :input-value="selected" label small>
                                    <span class="pr-2"> {{ item }} </span>
                                    <v-icon small @click="parent.selectItem(item)">close</v-icon>
                                </v-chip>
                            </template>
                        </v-combobox>
                    </template>
                </v-edit-dialog>
            </template>

            <template v-slot:item.rating="{ item }">
                <v-edit-dialog large :return-value.sync="item.rating" @save="save(item, 'rating')" save-text="保存"
                               cancel-text="取消">
                    <span v-if="item.rating != null">{{ item.rating }} 星</span>
                    <span v-else> - </span>
                    <template v-slot:input>
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-rating label="评分" v-model="item.rating" color="yellow accent-4" length="10"
                                  dense></v-rating>
                    </template>
                </v-edit-dialog>
            </template>

            <template v-slot:item.publisher="{ item }">
                <v-edit-dialog
                    large
                    :return-value.sync="item.publisher"
                    @save="save(item, 'publisher')"
                    save-text="保存"
                    cancel-text="取消">
                    {{ item.publisher }}
                    <template v-slot:input>
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-text-field v-model="item.publisher" label="出版社" counter></v-text-field>
                    </template>
                </v-edit-dialog>
            </template>

            <template v-slot:item.tags="{ item }">
                <v-edit-dialog large :return-value.sync="item.tags" @save="save(item, 'tags')" save-text="保存"
                               cancel-text="取消">
                    <span style="width: 200px" class="three-lines" v-if="item.tags">{{ item.tags.join("/") }}</span>
                    <span v-else> - </span>
                    <template v-slot:input>
                        <!-- TAGS -->
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-combobox
                            v-model="item.tags"
                            :items="item.tags"
                            label="标签列表"
                            :search-input.sync="tag_input"
                            hide-selected
                            multiple
                            small-chips>
                            <template v-slot:no-data>
                                <v-list-item>
                                    <span v-if="!tag_input">请输入新的标签名称</span>
                                    <div v-else>
                                        <span class="subheading">添加标签</span>
                                        <v-chip color="green lighten-3" label small rounded> {{ tag_input }}</v-chip>
                                    </div>
                                </v-list-item>
                            </template>
                            <!-- tag chip & close -->
                            <template v-slot:selection="{ attrs, item, parent, selected }">
                                <v-chip v-bind="attrs" color="green lighten-3" :input-value="selected" label small>
                                    <span class="pr-2"> {{ item }} </span>
                                    <v-icon small @click="parent.selectItem(item)">close</v-icon>
                                </v-chip>
                            </template>
                        </v-combobox>
                    </template>
                </v-edit-dialog>
            </template>

            <template v-slot:item.comments="{ item }">
                <v-edit-dialog large :return-value.sync="item.comments" @save="save(item, 'comments')" save-text="保存"
                               cancel-text="取消">
                    <span :title="item.comments" style="width: 300px" class="three-lines">{{ item.comments }}</span>
                    <template v-slot:input>
                        <div class="mt-4 text-h6">修改字段</div>
                        <v-textarea v-model="item.comments" label="简介"></v-textarea>
                    </template>
                </v-edit-dialog>
            </template>
            <template v-slot:item.douban_id="{ item }">
                <v-chip v-if='item.douban_id !== "Unknown"'
                        rounded
                        small
                        dark
                        color="green"
                        :href="`//book.douban.com/subject/${item.douban_id}`"
                        target="__blank">
                    <v-icon>explore</v-icon>
                    豆瓣
                </v-chip>
            </template>
            <template v-slot:item.actions="{ item }">
                <v-menu offset-y right>
                    <template v-slot:activator="{ on }">
                        <v-btn color="primary" small v-on="on">操作
                            <v-icon small>more_vert</v-icon>
                        </v-btn>
                    </template>
                    <v-list dense>
                        <v-list-item>
                            <v-list-item-title>
                                <a target="_blank" :href="`/book/${item.id}/edit`">编辑</a>
                            </v-list-item-title>
                        </v-list-item>
                        <v-list-item @click="delete_book(item)">
                            <v-list-item-title>删除</v-list-item-title>
                        </v-list-item>
                    </v-list>
                </v-menu>
            </template>

        </v-data-table>
        <!-- 小浮窗提醒 -->
        <v-snackbar v-model="snack" :timeout="1000" :color="snackColor">
            {{ snackText }}

            <template v-slot:action="{ attrs }">
                <v-btn v-bind="attrs" text @click="snack = false"> 关闭</v-btn>
            </template>
        </v-snackbar>
    </v-card>
</template>

<script>
export default {
    data: () => ({
        snack: false,
        snackColor: "",
        snackText: "",

        getdup: false,
        books_selected: [],
        tag_input: null,
        batch_op_tags: null,
        batch_add_tags: false,
        batch_delete_tags: false,
        show_batch_tags: false,
        search: "",
        page: 1,
        items: [],
        total: 0,
        loading: false,
        options: {sortBy: ["id"], sortDesc: [true]},
        headers: [
            {text: "封面", sortable: true, value: "id", width: "80px"},
            {text: "书名", sortable: false, value: "title"},
            {text: "ISBN", sortable: true, value: "isbn", width: "80px"},
            {text: "作者", sortable: true, value: "author", width: "100px"},
            {text: "评分", sortable: true, value: "rating", width: "100px"},
            {text: "出版社", sortable: true, value: "publisher"},
            {text: "标签", sortable: true, value: "tags", width: "100px"},
            {text: "简介", sortable: false, value: "comments"},
            {text: "链接", sortable: false, value: "douban_id", width: "80px"},
            {text: "操作", sortable: false, value: "actions"},
        ],
        progress: {
            done: 0,
            total: 0,
            status: "finish",
        },
    }),
    created() {
    },
    watch: {
        options: {
            handler() {
                this.getDataFromApi();
            },
            deep: true,
        },
    },
    methods: {
        getDataFromApi() {
            this.loading = true;
            const {sortBy, sortDesc, page, itemsPerPage} = this.options;

            var data = new URLSearchParams();
            if (page !== undefined) {
                data.append("page", page);
            }
            if (sortBy !== undefined) {
                data.append("sort", sortBy);
            }
            if (sortDesc !== undefined) {
                data.append("desc", sortDesc);
            }
            if (itemsPerPage !== undefined) {
                data.append("num", itemsPerPage);
            }
            if (this.search !== undefined) {
                data.append("search", this.search);
            }

            if (this.getdup) {
                data.append("dup", "true");
            }

            this.$backend("/admin/book/list?" + data.toString())
                .then((rsp) => {
                    if (rsp.err !== "ok") {
                        this.items = [];
                        this.total = 0;
                        this.$alert("error", rsp.msg);
                        return false;
                    }
                    this.items = rsp.items;
                    this.total = rsp.total;
                }).finally(() => {
                this.loading = false;
            });
        },
        auto_batch_op(detect, add_tag, delete_tag) {
            this.loading = true;
            this.$backend("/admin/book/list", {
                method: "POST",
                body: JSON.stringify({
                    book_list: this.books_selected.map((v) => {
                        return v.id;
                    }),
                    detect_books: detect,
                    add_tags: add_tag,
                    delete_tags: delete_tag,
                }),
            }).then((rsp) => {
                if (rsp.err !== "ok") {
                    this.$alert("error", rsp.msg);
                } else {
                    this.$alert("success", rsp.msg);
                }
                this.getDataFromApi();
            }).finally(() => {
                this.loading = false;
                if (add_tag || delete_tag) {
                    this.show_batch_tags = false
                }
            });
        },
        delete_book(book) {
            const user = this.$store.state.user
            if (user.pems.indexOf("D") > -1) {
                this.$alert("info", "当前用户禁止删除书籍，请联系管理员。", "/user/detail");
                return
            }
            this.loading = true;
            this.$backend("/book/" + book.id + "/delete", {
                method: "POST",
                body: "",
            }).then((rsp) => {
                if (rsp.err !== "ok") {
                    this.$alert("error", rsp.msg);
                }
                this.snack = true;
                this.snackColor = "success";
                this.snackText = rsp.msg;

                this.getDataFromApi();
            }).finally(() => {
                this.loading = false;
            });
        },
        save(book, field) {
            var edit = {};
            edit[field] = book[field];

            console.log("click save", field, book);
            this.saving = true;
            this.$backend("/book/" + book.id + "/edit", {
                method: "POST",
                body: JSON.stringify(edit),
            }).then((rsp) => {
                if (rsp.err === "ok") {
                    this.snack = true;
                    this.snackColor = "success";
                    this.snackText = rsp.msg;
                } else {
                    this.$alert("error", rsp.msg);
                }
            });
        },
    },
};
</script>

<style>
.three-lines {
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    white-space: normal;
}
</style>
