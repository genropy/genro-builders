<?xml version='1.0' encoding='UTF-8'?><xslt:stylesheet version="1.0" xmlns:xslt="http://www.w3.org/1999/XSL/Transform">
  <xslt:output method="html" encoding="UTF-8" indent="yes"></xslt:output>
  <xslt:template match="/urlset">
    <html>
      <head>
        <title>Sitemap</title>
      </head>
      <body>
        <h1>Sitemap</h1>
        <table>
          <thead>
            <tr>
              <th>URL</th>
              <th>Last modified</th>
              <th>Priority</th>
            </tr>
          </thead>
          <tbody>
            <xslt:for-each select="url">
              <tr>
                <td>
                  <a href="{loc}">
                    <xslt:value-of select="loc"></xslt:value-of>
                  </a>
                </td>
                <td>
                  <xslt:value-of select="lastmod"></xslt:value-of>
                </td>
                <td>
                  <xslt:value-of select="priority"></xslt:value-of>
                </td>
              </tr>
            </xslt:for-each>
          </tbody>
        </table>
      </body>
    </html>
  </xslt:template>
</xslt:stylesheet>
