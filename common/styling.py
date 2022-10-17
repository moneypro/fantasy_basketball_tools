def get_table_css() -> str:
    return """<style>
table {
    border: 1px solid;
    width: 100%;
}

th, td {
    border: 1px solid;
    text-align: left;
    padding: 8px;
}

tr:nth-child(even){background-color: #f2f2f2}
</style>"""