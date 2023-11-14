def webpage(value):
    html = f"""
            <!DOCTYPE html>
            <html>
            <body>
            <form action="./temperature">
            <input type="submit" value="temperature" />
            </form>
            <form action="./distance">
            <input type="submit" value="distance" />
            </form>
            <form action="./json">
            <input type="submit" value="json" />
            </form>
            <p>{value}</p>
            </body>
            </html>
            """
    return html