ThisBuild / version := "0.1.0-SNAPSHOT"

ThisBuild / scalaVersion := "2.13.16"

lazy val sicCore = (project in file("sic-core"))
  .settings(
    name := "sic-core",
    libraryDependencies ++= Seq(
      "org.typelevel" %% "cats-core" % "2.12.0"
    )
  )

lazy val sicGen = (project in file("sic-gen"))
  .dependsOn(sicCore)
  .settings(
    name := "sic-gen",
    libraryDependencies ++= Seq(
      "io.circle" %% "circle-yaml" % "0.15.1",
      "com.lihaoyi" %% "pprint" % "0.8.1"
    )
  )

lazy val root = (project in file("."))
  .aggregate(sicCore, sicGen)
  .settings(
    name := "sic"
  )
