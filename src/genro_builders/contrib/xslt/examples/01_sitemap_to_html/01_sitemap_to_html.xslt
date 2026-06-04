<?xml version='1.0' encoding='UTF-8'?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" indent="yes"></xsl:output>
  <xsl:template match="/urlset">
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
            <xsl:for-each select="url">
              <tr>
                <td>
                  <a href="{loc}">
                    <xsl:value-of select="loc"></xsl:value-of>
                  </a>
                </td>
                <td>
                  <xsl:value-of select="lastmod"></xsl:value-of>
                </td>
                <td>
                  <xsl:value-of select="priority"></xsl:value-of>
                </td>
              </tr>
            </xsl:for-each>
          </tbody>
        </table>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
