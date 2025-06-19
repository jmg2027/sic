```bash
### clone & create skeleton #########################################
git clone git@github.com:<ID>/sic.git && cd sic

### tooling
echo 'addSbtPlugin("org.scalameta" % "sbt-scalafmt" % "2.5.2")' >> project/plugins.sbt
echo 'addSbtPlugin("ch.epfl.scala" % "sbt-scalafix" % "0.11.1")' >> project/plugins.sbt
sbt reload scalafmtGenerateConfig

### code scaffold (simplified)
mkdir -p sic-core/src/main/scala/{sic,sic/primitives,sic/dsl,sic/catalogue}
mkdir -p sic-core/src/test/scala/sic
touch sic-core/src/main/scala/sic/primitives/{Expr.scala,Stmt.scala,Prim.scala}
touch sic-core/src/main/scala/sic/{Format.scala,BitPattern.scala}
touch sic-core/src/main/scala/sic/catalogue/Catalogue.scala

### first compile pass
sbt compile

### YAML export demo
mkdir -p generated
sbt "sicGen/runMain sicgen.YamlExport" > generated/sic.yaml
git add .
git commit -m "feat: bootstrap SIC skeleton"
git push
```
