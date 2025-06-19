ThisBuild / version := "0.1.0-SNAPSHOT"

ThisBuild / scalaVersion := "2.13.16"

lazy val sicCore = (project in file("sic-core"))
  .settings(
    name := "sic-core",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.12.0",
      "org.scalatest" %% "scalatest" % "3.2.17" % Test
    )
  )

lazy val sicGen = (project in file("sic-gen"))
  .dependsOn(sicCore)
  .settings(
    name := "sic-gen",
    libraryDependencies ++= Seq(
      "io.circe" %% "circe-yaml" % "0.15.1",
      "io.circe" %% "circe-generic" % "0.14.6",
      "com.lihaoyi" %% "pprint" % "0.8.1"
    )
  )

lazy val root = (project in file("."))
  .aggregate(sicCore, sicGen)
  .settings(
    name := "sic",
    addCommandAlias("fmt", "scalafmtAll; scalafmtSbt"),
    addCommandAlias("check", "scalafmtCheckAll; Test/compile")
  )
